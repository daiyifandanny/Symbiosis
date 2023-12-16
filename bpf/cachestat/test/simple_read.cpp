#ifdef __INTELLISENSE__
#pragma diag_suppress 266
#endif

#include <iostream>
#include <fstream>
#include <sys/mman.h>
#include "cxxopts.hpp"
#include <fcntl.h>
#include <unistd.h>
#include <cstdlib>
#include <vector>
#include <sys/sdt.h>
#include <sys/stat.h>
#include <random>
#include <chrono>
#include <cassert>
#include <x86intrin.h>

using namespace std;


const char* filename = "/nvme/test/tsukushi.txt";
const char* trace_filename = ".trace";
const char* step_time_filename = "step_time.txt";
float frequency = 3700;
uint64_t size = 1024 * 1024 * 1024;
int page_size = 4096;


std::string random_string( size_t length )
{
    auto randchar = []() -> char
    {
        const char charset[] =
        "0123456789"
        "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
        "abcdefghijklmnopqrstuvwxyz";
        const size_t max_index = (sizeof(charset) - 1);
        return charset[ rand() % max_index ];
    };
    std::string str(length,0);
    std::generate_n( str.begin(), length, randchar );
    return str;
}


// pin the current running thread to certain cpu core.
// core_id starts from 1, return 0 on success.
inline int pin_to_cpu_core(int core_id) {
  if (core_id < 1) return -1;
  cpu_set_t cpuset;
  CPU_ZERO(&cpuset);
  CPU_SET(core_id - 1, &cpuset);
  int s = pthread_setaffinity_np(pthread_self(), sizeof(cpu_set_t), &cpuset);
  return s;
}

template <typename Clock = std::chrono::high_resolution_clock>
class stopwatch
{
    const typename Clock::time_point start_point;
public:
    stopwatch() : 
        start_point(Clock::now())
    {}

    template <typename Rep = typename Clock::duration::rep, typename Units = typename Clock::duration>
    Rep elapsed_time() const
    {
        std::atomic_thread_fence(std::memory_order_relaxed);
        auto counted_time = std::chrono::duration_cast<Units>(Clock::now() - start_point).count();
        std::atomic_thread_fence(std::memory_order_relaxed);
        return static_cast<Rep>(counted_time);
    }
};

using precise_stopwatch = stopwatch<>;
using system_stopwatch = stopwatch<std::chrono::system_clock>;
using monotonic_stopwatch = stopwatch<std::chrono::steady_clock>;

class SkewedWorkload {
private:
  uint64_t range_start_;
  uint64_t range_end_;
  uint64_t hotspot_start_;
  uint64_t hotspot_end_;
  uint64_t hotspot_size_;
  uint64_t other_size_;
  float hotspot_ratio_;
public:
  SkewedWorkload(uint64_t range_start, uint64_t range_end, uint64_t hotspot_start, uint64_t hotspot_end, float hotspot_ratio)
    : range_start_(range_start), range_end_(range_end), hotspot_start_(hotspot_start), hotspot_end_(hotspot_end),
    hotspot_size_(hotspot_end - hotspot_start), other_size_(range_end - range_start - hotspot_size_), hotspot_ratio_(hotspot_ratio) {
    std::srand(811);
  } 

  uint64_t Target() {
    bool hotspot = std::rand() % 1000 < hotspot_ratio_ * 1000;
    if (hotspot) {
      return hotspot_start_ + std::rand() % hotspot_size_;
    } else {
      uint64_t temp = std::rand() % other_size_;
      uint64_t ret = range_start_ + temp;
      if (temp >= hotspot_start_ - range_start_) ret += hotspot_size_;
      return ret;
    }
  }
};


int main(int argc, char** argv) {
    bool is_mmap, random, pause, commandline, direct, sequence, cached;
    int read_ahead, step, advise, dist;
    uint64_t read_size, force_stop, write_size, num_reads;
    float size_factor;

    cxxopts::Options commandline_options("leveldb read test", "Testing leveldb read performance.");
    commandline_options.add_options()
            ("w,write", "write", cxxopts::value<uint64_t>(write_size)->default_value("0"))
            ("n,num_reads", "read", cxxopts::value<uint64_t>(num_reads)->default_value("10000000"))
            ("m,mmap", "mmap", cxxopts::value<bool>(is_mmap)->default_value("false"))
            ("r,random", "random", cxxopts::value<bool>(random)->default_value("false"))
            ("random_sequence", "random sequence", cxxopts::value<bool>(sequence)->default_value("false"))
            ("a,ahead", "read ahead", cxxopts::value<int>(read_ahead)->default_value("256"))
            ("s,step", "read step", cxxopts::value<int>(step)->default_value("1"))
            ("read_size", "read size", cxxopts::value<uint64_t>(read_size)->default_value("1"))
            ("p, pause", "pause", cxxopts::value<bool>(pause)->default_value("false"))
            ("advise", "do madvise", cxxopts::value<int>(advise)->default_value("0"))
            ("force_stop", "force stop", cxxopts::value<uint64_t>(force_stop)->default_value("0"))
            ("c, commandline", "commandline", cxxopts::value<bool>(commandline)->default_value("false"))
            ("cached", "cached read", cxxopts::value<bool>(cached)->default_value("false"))
            ("d, direct", "O_DIRECT", cxxopts::value<bool>(direct)->default_value("false"))
            ("distribution", "workload distribution", cxxopts::value<int>(dist)->default_value("0"))
            ("size_factor", "0.2-1", cxxopts::value<float>(size_factor)->default_value("1"));
    auto result = commandline_options.parse(argc, argv);
    step = step < read_size ? read_size : step;
    read_size = read_size * page_size;
    size /= size_factor;
    int num_pages = size / page_size;
    printf("Max_pages: %d\n", num_pages);
    if (!direct) read_size -= 1;

    pin_to_cpu_core(1);
    // string read_head_command = "sudo blockdev --setra " + to_string(read_ahead) + " /dev/nvme1n1p1";
    // system(read_head_command.c_str());
    if (!cached) system("sync; echo 3 | sudo tee /proc/sys/vm/drop_caches; sudo fstrim -a -v");

    if (write_size != 0) {
        int fd = open(filename, O_WRONLY | O_CREAT | O_TRUNC, 0777);
        // string page(page_size, 'a');

        for (int i = 0; i < write_size; ++i) {
            string page = random_string(page_size);
            write(fd, page.c_str(), page_size);
        }

        close(fd);
        DTRACE_PROBE2(leveldb, bcache_start_probe, 0, 0);
        DTRACE_PROBE2(leveldb, bcache_end_probe, 0, 0);
        DTRACE_PROBE2(leveldb, search1_start_probe, 0, 0);
        DTRACE_PROBE2(leveldb, search1_end_probe, 0, 0);
        // DTRACE_PROBE2(leveldb, search2_start_probe, 0, 0);
        // DTRACE_PROBE2(leveldb, search2_end_probe, 0, 0);
        // DTRACE_PROBE2(leveldb, pcache_access1, 0, 0);
        DTRACE_PROBE2(leveldb, pcache_access2, 0, 0);
        return 0;
    }

    int o_flag = direct ? O_RDONLY | O_DIRECT : O_RDONLY;
    int fd = open(filename, o_flag);
    char* mmap_base = static_cast<char*>(mmap(nullptr, num_pages * page_size, PROT_READ, MAP_SHARED, fd, 0));
    if (advise != 0) {
        if (is_mmap) madvise(mmap_base, num_pages * page_size, advise);
        else posix_fadvise(fd, 0, num_pages * page_size, advise);
    }
    void* buffer;
    posix_memalign(&buffer, page_size, read_size);
    
    struct stat buf;
    fstat(fd, &buf);
    uint64_t ino = buf.st_ino;

    std::srand(915);
    mt19937 generator(210);
    uniform_int_distribution<int> distribution(0, num_pages - 1);
    SkewedWorkload skewed_workload(0, num_pages, 0, num_pages / 5, 0.8);

    std::string size_factor_str = std::to_string(size_factor);
    size_factor_str.erase(size_factor_str.find_last_not_of('0') + 1, std::string::npos);
    size_factor_str.erase(size_factor_str.find_last_not_of('.') + 1, std::string::npos);
    std::string trace_file = to_string(dist) + "_" + size_factor_str + trace_filename;
    ofstream trace(trace_file.c_str()), step_time(step_time_filename);
    sleep(1);
    uint64_t limit = random ? num_reads : num_pages;
    uint64_t wait = 0, total_reads = 0, step_timer = 0;
    uint32_t dummy;
    vector<uint64_t> random_sequence;
    if (sequence) {
        for (uint64_t i = 0; i < num_pages; i += step) random_sequence.push_back(i);
        random_shuffle(random_sequence.begin(), random_sequence.end());
        limit = random_sequence.size();
    }

    precise_stopwatch timer;
    for (uint64_t i = 0; i < limit;) {
        if (force_stop != 0 && i > force_stop) break;
        if (commandline && i == wait) {
            uint64_t step;
            cout << "step: ";
            cin >> step;
            wait += step;
        }        

        uint64_t target;
        if (dist == 1) {
            target = skewed_workload.Target();
            i += 1;
        } else if (random) {
            target = distribution(generator);
            i += 1;
        } else if (sequence) {
            target = random_sequence[i];
            i += 1;
        } else {
            target = i;
            i += step;
        }
        trace << target << "\n";

        DTRACE_PROBE2(leveldb, fcache_start_probe, ino, target);
        // step_timer = __rdtscp(&dummy);
        if (is_mmap) memcpy(buffer, mmap_base + target * page_size, read_size);
        else {
            int ret = (int) pread(fd, buffer, read_size, target * page_size);
            assert(ret >= page_size - 1);
            total_reads += ret;
        }
        // step_time << target << " " << (__rdtscp(&dummy) - step_timer) / frequency << "\n";
        DTRACE_PROBE2(leveldb, fcache_end_probe, ino, target);
        DTRACE_PROBE2(leveldb, pcache_access1, ino, target);
        if (pause) usleep(100);
    }
    auto diff = timer.elapsed_time<>();
    printf("Total Time: %.2f s Total Read: %lu pages\n", diff / (float) 1000000000, total_reads / 4096);

    free(buffer);
    munmap(mmap_base, num_pages * page_size);
    close(fd);
    return 0;
}
