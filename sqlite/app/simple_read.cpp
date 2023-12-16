#include <iostream>
#include <sqlite3.h>
#include <cassert>
#include <cstdlib>
#include <random>
#include "cxxopts.hpp"
#include <sys/sdt.h>
#include <chrono>


using namespace std;

const int key_size = 16;
const int num_entries = 10000000;
const int num_reads = num_entries / 10;
const char* db_location = "/nvme/sqlite2/test.db";


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
    bool is_write, is_mmap, is_random, pause;
    int cache_size;
    float read_ratio;
    string sql, value(80, 'a');

    cxxopts::Options commandline_options("leveldb read test", "Testing leveldb read performance.");
    commandline_options.add_options()
            ("w,write", "write", cxxopts::value<bool>(is_write)->default_value("false"))
            ("m,mmap", "mmap", cxxopts::value<bool>(is_mmap)->default_value("false"))
            ("r,random", "random", cxxopts::value<bool>(is_random)->default_value("false"))
            ("read_ratio", "read ratio", cxxopts::value<float>(read_ratio)->default_value("1"))
            ("p,pause", "pause", cxxopts::value<bool>(pause)->default_value("false"))
            ("cache_size", "cache size", cxxopts::value<int>(cache_size)->default_value("1000000"));
    auto result = commandline_options.parse(argc, argv);

    sqlite3* db;
    sqlite3_stmt* statement;
    int ret;

    if (is_write) {
        string prefix = "rm ";
        string command = prefix + db_location;
        system(command.c_str());
    }
    system("sync; echo 3 | sudo tee /proc/sys/vm/drop_caches; sudo fstrim -av");
    pin_to_cpu_core(1);

    mt19937 generator(915);
    uniform_int_distribution<int> distribution(0, num_entries - 1);

    ret = sqlite3_open(db_location, &db);
    assert(ret == SQLITE_OK);
    sql = "PRAGMA cache_size=-" + to_string(cache_size);
    ret = sqlite3_exec(db, sql.c_str(), nullptr, nullptr, nullptr);
    assert(ret == SQLITE_OK);
    ret = sqlite3_exec(db, "PRAGMA page_size=4096", nullptr, nullptr, nullptr);
    assert(ret == SQLITE_OK);
    
    if (is_mmap) {
        ret = sqlite3_exec(db, "PRAGMA mmap_size=2147483647", nullptr, nullptr, nullptr);
        assert(ret == SQLITE_OK);        
    }

    ret = sqlite3_exec(db, "begin transaction", nullptr, nullptr, nullptr);
    assert(ret == SQLITE_OK);

    precise_stopwatch timer;
    if (is_write) {
        ret = sqlite3_exec(db, "CREATE TABLE kv (key integer primary key, value text)", nullptr, nullptr, nullptr);
        assert(ret == SQLITE_OK);

        string skeleton = "INSERT INTO kv VALUES (?, ?)";
        ret = sqlite3_prepare_v2(db, skeleton.c_str(), skeleton.length(), &statement, nullptr);
        assert(ret == SQLITE_OK);
        
        for (int i = 0; i < num_entries; ++i) {
            int key = i;
            // string key_string = form_key(i);
            ret = sqlite3_bind_int(statement, 1, i);
            assert(ret == SQLITE_OK);
            ret = sqlite3_bind_text(statement, 2, value.c_str(), value.length(), nullptr);
            assert(ret == SQLITE_OK);
            ret = sqlite3_step(statement);
            assert(ret == SQLITE_DONE);
            ret = sqlite3_clear_bindings(statement);
            assert(ret == SQLITE_OK);
            ret = sqlite3_reset(statement);
            assert(ret == SQLITE_OK);
        }

        // ret = sqlite3_exec(db, "CREATE INDEX ikv ON kv(key)", nullptr, nullptr, nullptr);
        // assert(ret == SQLITE_OK);

        DTRACE_PROBE2(leveldb, search1_start_probe, 0, 0);
        DTRACE_PROBE2(leveldb, search1_end_probe, 0, 0);
        DTRACE_PROBE2(leveldb, bcache_start_probe, 0, 0);
        DTRACE_PROBE2(leveldb, bcache_end_probe, 0, 0);
        // DTRACE_PROBE2(leveldb, pcache_access1, 0, 0);
        DTRACE_PROBE2(leveldb, pcache_access2, 0, 0);
    } else {
        string skeleton = "SELECT * FROM kv where key = ?";
        ret = sqlite3_prepare_v2(db, skeleton.c_str(), skeleton.length(), &statement, nullptr);
        assert(ret == SQLITE_OK);

        int num_queries = is_random ? num_reads : num_entries;
        for (int i = 0; i < num_queries; ++i) {
            int key = is_random ? distribution(generator) : i;
            key = (int) (key * read_ratio);
            string key_string = form_key(key);
            ret = sqlite3_bind_int(statement, 1, key);
            assert(ret == SQLITE_OK);
            ret = sqlite3_step(statement);
            assert(ret == SQLITE_ROW);
            if (i == 0) {
                printf("%s: %s\n", sqlite3_column_text(statement, 0), sqlite3_column_text(statement, 1));
            }
            ret = sqlite3_clear_bindings(statement);
            assert(ret == SQLITE_OK);
            ret = sqlite3_reset(statement);
            assert(ret == SQLITE_OK);
        }
    }
    auto diff = timer.elapsed_time<>();
    printf("Total Time: %.2f s\n", diff / (float) 1000000000);

    ret = sqlite3_exec(db, "end transaction", nullptr, nullptr, nullptr);
    assert(ret == SQLITE_OK);
    ret = sqlite3_finalize(statement);
    assert(ret == SQLITE_OK);
    sqlite3_close(db);

    return 0;
}

