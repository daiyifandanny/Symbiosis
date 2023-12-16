#ifdef __INTELLISENSE__
#pragma diag_suppress 167
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

using namespace std;


const char* filename = "/nvme/test/btree.txt";
const char* trace_filename = "temp.txt";
uint64_t size = 1024 * 1024 * 1024;
int page_size = 4096;
int num_pages = size / page_size;
int num_ops = 200000;


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


int main(int argc, char** argv) {
    bool is_write, is_mmap, random, pause;
    int read_ahead, step, read_size, advise, focus_num;
    float focus_ratio;

    cxxopts::Options commandline_options("leveldb read test", "Testing leveldb read performance.");
    commandline_options.add_options()
            ("w,write", "write", cxxopts::value<bool>(is_write)->default_value("false"))
            ("m,mmap", "mmap", cxxopts::value<bool>(is_mmap)->default_value("false"))
            ("r,random", "random", cxxopts::value<bool>(random)->default_value("false"))
            ("a,ahead", "read ahead", cxxopts::value<int>(read_ahead)->default_value("256"))
            ("s,step", "read step", cxxopts::value<int>(step)->default_value("1"))
            ("read_size", "read size", cxxopts::value<int>(read_size)->default_value("4096"))
            ("p, pause", "pause", cxxopts::value<bool>(pause)->default_value("false"))
            ("focus_ratio", "pause", cxxopts::value<float>(focus_ratio)->default_value("0.2"))
            ("focus_num", "pause", cxxopts::value<int>(focus_num)->default_value("5"))
            ("advise", "do madvise", cxxopts::value<int>(advise)->default_value("0"));
    auto result = commandline_options.parse(argc, argv);
    int num_entries = size / read_size;

    pin_to_cpu_core(1);
    string read_head_command = "sudo blockdev --setra " + to_string(read_ahead) + " /dev/nvme0n1";
    system(read_head_command.c_str());

    if (is_write) {
        int fd = open(filename, O_WRONLY | O_CREAT | O_TRUNC, 0777);
        string page(page_size, 'a');

        for (int i = 0; i < num_pages; ++i) {
            write(fd, page.c_str(), page_size);
        }

        close(fd);
        // DTRACE_PROBE2(leveldb, bcache_start_probe, 0, 0);
        // DTRACE_PROBE2(leveldb, bcache_end_probe, 0, 0);
        DTRACE_PROBE2(leveldb, search1_start_probe, 0, 0);
        DTRACE_PROBE2(leveldb, search1_end_probe, 0, 0);
        // DTRACE_PROBE2(leveldb, pcache_access1, 0, 0);
        DTRACE_PROBE2(leveldb, pcache_access2, 0, 0);
    }

    system("sync; echo 3 | sudo tee /proc/sys/vm/drop_caches; sudo fstrim -a -v");

    int fd = open(filename, O_RDONLY);
    char* mmap_base = static_cast<char*>(mmap(nullptr, size, PROT_READ, MAP_SHARED, fd, 0));
    if (advise != 0) {
        madvise(mmap_base, size, advise);
        posix_fadvise(fd, 0, size, advise);
    }
    char* buffer = new char[read_size];
    
    struct stat buf;
    fstat(fd, &buf);
    uint64_t ino = buf.st_ino;


    mt19937 generator(210);
    uniform_int_distribution<int> focus_distribution(0, (int) floor((num_entries - 1) * focus_ratio));
    uniform_int_distribution<int> other_distribution((int) ceil((num_entries - 1) * focus_ratio), (int) (num_entries - 1));

    precise_stopwatch timer;
    for (int i = 0; i < num_ops; ++i) {
        for (int j = 0; j < focus_num + 1; ++j) {
            bool focused = j != focus_num;
            
            uint64_t target = focused ? focus_distribution(generator) : other_distribution(generator);
            
            if (focused) DTRACE_PROBE2(leveldb, fcache_start_probe, 0, 0);
            else DTRACE_PROBE2(leveldb, bcache_start_probe, 0, 0);

            if (is_mmap) memcpy(buffer, mmap_base + target * read_size, read_size);
            else pread(fd, buffer, read_size, target * read_size);
            for (uint64_t offset = target * read_size / page_size; offset <= (target * read_size + read_size - 1) / page_size; ++offset) {
                DTRACE_PROBE2(leveldb, pcache_access1, ino, offset);
            }

            if (focused) DTRACE_PROBE2(leveldb, fcache_end_probe, 0, 0);
            else DTRACE_PROBE2(leveldb, bcache_end_probe, 0, 0);

            if (pause) usleep(10);
        }
    }
    auto diff = timer.elapsed_time<>();
    printf("Total Time: %.2f s\n", diff / (float) 1000000000);


    // std::srand(915);
    // vector<uint64_t> sequence;
    // if (random) {
    //     for (int i = 0; i < num_pages; ++i) sequence.push_back(i);
    //     random_shuffle(sequence.begin(), sequence.end());
    // } else {
    //     for (int i = 0; i < num_pages; i += step) sequence.push_back(i);
    // }

    // sleep(1);
    // for (uint64_t i: sequence) {
    //     DTRACE_PROBE2(leveldb, fcache_start_probe, ino, i);
    //     if (is_mmap) memcpy(buffer, mmap_base + i * page_size, read_size);
    //     else pread(fd, buffer, read_size, i * page_size);
    //     DTRACE_PROBE2(leveldb, fcache_end_probe, ino, i);
    //     if (pause) usleep(10);
    // }

    delete[] buffer;
    munmap(mmap_base, size);
    close(fd);
    return 0;
}
