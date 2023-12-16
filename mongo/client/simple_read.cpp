#include <cstdint>
#include <iostream>
#include <cassert>
#include <vector>
#include <bsoncxx/json.hpp>
#include <mongocxx/client.hpp>
#include <mongocxx/stdx.hpp>
#include <mongocxx/uri.hpp>
#include <mongocxx/instance.hpp>
#include <cxxopts.hpp>
#include <random>

using bsoncxx::builder::basic::make_document;
using bsoncxx::builder::basic::kvp;
using namespace std;


const string database_name = "kanade";
const string collection_name = "test";
const int num_entries = 8000000;
const int num_reads = num_entries / 100;


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
    bool is_write, is_mmap, is_random;

    cxxopts::Options commandline_options("leveldb read test", "Testing leveldb read performance.");
    commandline_options.add_options()
            ("w,write", "write", cxxopts::value<bool>(is_write)->default_value("false"))
            ("m,mmap", "mmap", cxxopts::value<bool>(is_mmap)->default_value("false"))
            ("r,random", "random", cxxopts::value<bool>(is_random)->default_value("false"));
    auto result = commandline_options.parse(argc, argv);

    mongocxx::instance instance;
    mongocxx::client client(mongocxx::uri("mongodb://localhost:21021"));
    mongocxx::database db = client[database_name];
    mongocxx::collection collection = db[collection_name];

    if (is_write) {
        collection.drop();
    }

    system("sync; echo 3 | sudo tee /proc/sys/vm/drop_caches; sudo fstrim -a -v");

    precise_stopwatch timer;
    if (is_write) {
        string value(80, 'a');

        mongocxx::collection collection = db[collection_name];
        vector<bsoncxx::v_noabi::document::value> docs;
        for (int i = 0; i < num_entries; ++i) {
            docs.push_back(make_document(kvp("_id", i), kvp("value", value)));
        }
        printf("bulk prepared\n");
        // for (int i = 0; i < num_entries; ++i) {
        //     collection.insert_one(std::move(docs[i]));
        // }
        collection.insert_many(docs);
        assert(collection.count_documents({}) == num_entries);
        printf("bulk loaded\n");
        collection.create_index(make_document(kvp("_id", 1)));
        printf("index created\n");
    } else {
        mt19937 generator(210);
        uniform_int_distribution<int> distribution(0, num_entries - 1);

        int num_queries = is_random ? num_reads : num_entries;
        for (int i = 0; i < num_queries; ++i) {
            int target = is_random ? distribution(generator) : i;
            auto result = collection.find_one(make_document(kvp("_id", target)));
            assert(result);
            if (i == 0) cout << bsoncxx::to_json(*result) << "\n";
        }
    }
    auto diff = timer.elapsed_time<>();
    printf("Total Time: %.2f s\n", diff / (float) 1000000000);

    return 0;
}

