#include <iostream>
#include <wiredtiger.h>
#include <cassert>
#include <cstdlib>
#include <random>
#include "cxxopts.hpp"
#include <sys/sdt.h>
#include <chrono>
#include "../src/include/external.h"
#include "adapter.h"
#include <fstream>
#include <sys/time.h>


using namespace std;


const int key_size = 16;
const int value_size = 72;
const int num_entries = 50000000;
// const int default_reads = num_entries / 10;
const int default_reads = 10000000;
const char* db_location = "/nvme/wiredtiger";


int print_cursor(WT_CURSOR *cursor) {
    const char *desc, *pvalue;
    uint64_t value;
    int ret;

    while (
        (ret = cursor->next(cursor)) == 0 &&
        (ret = cursor->get_value(cursor, &desc, &pvalue, &value)) == 0)
            printf("%s=%s\n", desc, pvalue);

    return (ret == WT_NOTFOUND ? 0 : ret);
}

uint64_t NowMicros() {
    static constexpr uint64_t kUsecondsPerSecond = 1000000;
    struct ::timeval tv;
    ::gettimeofday(&tv, nullptr);
    return static_cast<uint64_t>(tv.tv_sec) * kUsecondsPerSecond + tv.tv_usec;
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

string form_key(int key_num) {
    string key_string = to_string(key_num);
    return string(key_size - key_string.length(), '0') + key_string;
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
    bool is_write, is_mmap, is_random, pause, cached;
    uint64_t cache_size, memory_size; 
    int compressed_size, num_reads;
    float read_ratio;
    string sql, compression_library, trace_filename, output_filename;

    cxxopts::Options commandline_options("leveldb read test", "Testing leveldb read performance.");
    commandline_options.add_options()
            ("w,write", "write", cxxopts::value<bool>(is_write)->default_value("false"))
            ("m,mmap", "mmap", cxxopts::value<bool>(is_mmap)->default_value("false"))
            ("r,random", "random", cxxopts::value<bool>(is_random)->default_value("false"))
            ("read_ratio", "read ratio", cxxopts::value<float>(read_ratio)->default_value("1"))
            ("p,pause", "pause", cxxopts::value<bool>(pause)->default_value("false"))
            ("cache_size", "cache size", cxxopts::value<uint64_t>(cache_size)->default_value("268500000"))
            ("memory_size", "memory size", cxxopts::value<uint64_t>(memory_size)->default_value("1074000000"))
            ("c,compression", "compression", cxxopts::value<int>(compressed_size)->default_value("8"))
            ("n,num_reads", "num_reads", cxxopts::value<int>(num_reads)->default_value("0"))
            ("cached", "cached", cxxopts::value<bool>(cached)->default_value("false"))
            ("compression_library", "compression library", cxxopts::value<string>(compression_library)->default_value("snappy"))
            ("output", "output file", cxxopts::value<string>(output_filename)->default_value("default.out"))
            ("trace", "trace input", cxxopts::value<string>(trace_filename)->default_value(""));
    auto result = commandline_options.parse(argc, argv);
    if (num_reads == 0) num_reads = default_reads;

    WT_CONNECTION *connection;
    WT_CURSOR *cursor, *cursor2;
    WT_SESSION *session;
    const char *k, *v;
    int ret;

    if (is_write) {
        string prefix = "rm -rf ";
        string command = prefix + db_location + "/*";
        system(command.c_str());
    }
    if (!cached) system("sync; echo 3 | sudo tee /proc/sys/vm/drop_caches; sudo fstrim -av");

    string open_config = "create,cache_size=" + to_string(cache_size) + ",eviction_target=85,eviction_trigger=95,eviction=(threads_min=1,threads_max=1)";
    if (compressed_size != 0) {
        open_config += ",extensions=[/usr/local/lib/libwiredtiger_snappy.so,/usr/local/lib/libwiredtiger_lz4.so,/usr/local/lib/libwiredtiger_zstd.so,/usr/local/lib/libwiredtiger_zlib.so]";
    }
    ret = wiredtiger_open(db_location, nullptr, open_config.c_str(), &connection);
    assert(ret == 0);
    ret = connection->open_session(connection, nullptr, nullptr, &session);
    assert(ret == 0);

    Adapter::Init(memory_size, cache_size, connection);
    Adapter* adapter = Adapter::instance;

    pin_to_cpu_core(1);
    // int num_queries = is_random ? num_reads : num_entries - 1;
    int num_queries = num_reads;
    precise_stopwatch timer;
    if (is_write) {
        string create_config = "key_format=S,value_format=S,checksum=off,leaf_page_max=20KB,internal_page_max=512MB";
        if (compressed_size != 0) {
            // create_config += ",block_compressor=" + compression_library;
            if (compression_library == "zstd")  create_config += ",block_compressor=zstd";
            else if (compression_library == "snappy") create_config += ",block_compressor=snappy";
            else if (compression_library == "lz4")  create_config += ",block_compressor=lz4";
            else if (compression_library == "zlib")  create_config += ",block_compressor=zlib";
        }
        ret = session->create(session, "table:kanade", create_config.c_str());
        assert(ret == 0);
        ret = session->open_cursor(session, "table:kanade", nullptr, nullptr, &cursor);
        assert(ret == 0);

        mt19937 generator(210);
        uniform_int_distribution<char> distribution(48, 126);

        for (int i = 0; i < num_entries; ++i) {
            string key_string = std::move(form_key(i));
            cursor->set_key(cursor, key_string.c_str());
            // cursor->set_key(cursor, i);
            // printf("%d\n", i);
            string value;
            for (int j = 0; j < compressed_size; ++j) {
                value += distribution(generator);
            }
            for (int j = 0; j < value_size - compressed_size; ++j) {
                value += "0";
            }
            cursor->set_value(cursor, value.c_str());
            ret = cursor->insert(cursor);
            assert(ret == 0);
            // ret = cursor->reset(cursor);
            // assert(ret == 0);
        }

        DTRACE_PROBE2(leveldb, search1_start_probe, 0, 0);
        DTRACE_PROBE2(leveldb, search1_end_probe, 0, 0);
        DTRACE_PROBE2(leveldb, bcache_start_probe, 0, 0);
        DTRACE_PROBE2(leveldb, bcache_end_probe, 0, 0);
        // DTRACE_PROBE2(leveldb, pcache_access1, 0, 0);
        DTRACE_PROBE2(leveldb, pcache_access2, 0, 0);
    } else {
        remove("wt_trace_disk.txt");
        remove("wt_trace_eviction.txt");
        remove("wt_trace_app.txt");

        mt19937 generator(210);
        uniform_int_distribution<int> distribution(0, (int) ((num_entries - 1)));

        ret = session->open_cursor(session, "table:kanade", nullptr, nullptr, &cursor);
        assert(ret == 0);

        ifstream trace_file(trace_filename.c_str());
        ofstream output_file(output_filename.c_str());

        // int num_queries = is_random ? num_reads : 10000;
        uint64_t timer1 = NowMicros();
        for (int i = 0; i < num_queries; ++i) {
            int key = is_random ? distribution(generator) : i;
            if (trace_file) trace_file >> key;
            if (key >= num_entries) key = num_entries - 1;
            // if (rand() % 5 && key > num_entries / 2) key -= num_entries / 2;
            // if (rand() % 5 && key < num_entries / 2) key += num_entries / 2;
            string key_string = std::move(form_key((int) floor(key * read_ratio)));
            // printf("key: %s\n", key_string.c_str());
            cursor->set_key(cursor, key_string.c_str());
            // cursor->set_key(cursor, key);
            ret = cursor->search(cursor);
            if (ret != 0) {
                printf("key: %s\n", key_string.c_str());
                assert(false);
            }
            if (i == 0) {
                cursor->get_key(cursor, &k);
                cursor->get_value(cursor, &v);
                printf("key:%s, value:%s\n", k, v);
            }
            // if (app_cache_hit == 0) {
            //     printf("key %d app_cache_hit %u app_cache_addr %lu app_cache_size %lu kernel_cache_time %lu kernel_cache_start %lu kernel_cache_size %lu\n",
            //             key, app_cache_hit, app_cache_id / 4096, app_cache_size, kernel_cache_time, kernel_cache_start, kernel_cache_size);                
            // }

            adapter->Record(app_cache_id, 4096, app_cache_id / 4096, 
                                        app_cache_size * 1.00, app_cache_hit == 1, kernel_cache_time < 5000);
            app_cache_hit = 0;
            app_cache_id = 0;
            app_cache_size = 0;
            kernel_cache_time = 0;
            kernel_cache_start = 0;
            kernel_cache_size = 0;
            // ret = cursor->reset(cursor);
            // assert(ret == 0);

            if ((i + 1) % (num_queries / 1000) == 0) {
                uint64_t temp = NowMicros();
                output_file << temp - timer1 << "\n";
                timer1 = temp;
            }
        }

        // auto diff = timer.elapsed_time<>();
        // printf("Total Time: %.2f s\n", diff / (float) 1000000000);        

        // for (int i = 0; i < num_queries; ++i) {
        //     int key = is_random ? distribution(generator) : i;
        //     // if (rand() % 5 && key > num_entries / 2) key -= num_entries / 2;
        //     // if (rand() % 5 && key < num_entries / 2) key += num_entries / 2;
        //     string key_string = std::move(form_key((int) floor(key * read_ratio)));
        //     cursor->set_key(cursor, key_string.c_str());
        //     ret = cursor->search(cursor);
        //     assert(ret == 0);
        //     if (i == 0) {
        //         cursor->get_key(cursor, &k);
        //         cursor->get_value(cursor, &v);
        //         printf("key:%s, value:%s\n", k, v);
        //     }
        //     printf("app_cache_hit %u app_cache_addr %lu app_cache_size %lu kernel_cache_time %lu kernel_cache_start %lu kernel_cache_size %lu\n",
        //             app_cache_hit, app_cache_id, app_cache_size, kernel_cache_time, kernel_cache_start, kernel_cache_size);
        //     // ret = cursor->reset(cursor);
        //     // assert(ret == 0);
        // }
    }
    auto diff = timer.elapsed_time<>();
    printf("Total Time: %.2f s\n", diff / (float) 1000000000);

    // ret = session->open_cursor(session, "statistics:", NULL, NULL, &cursor2);
    // assert(ret == 0);
    // print_cursor(cursor2);

    ret = session->close(session, nullptr);
    assert(ret == 0);
    ret = connection->close(connection, nullptr);
    assert(ret == 0);

    return 0;
}

