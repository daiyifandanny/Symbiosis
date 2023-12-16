#include "cache.h"
#include "rocksdb/cache.h"
#include "rocksdb/db.h"
#include "util/coding.h"
#include <vector>
#include <limits>
#include "stats.h"
#include <malloc.h>
#include <google/dense_hash_set>
#include <memory>


using std::vector;
using std::pair;
using namespace leveldb;
using ROCKSDB_NAMESPACE::DB;
using ROCKSDB_NAMESPACE::Slice;


class Adapter;

void DeleteNullptr(const Slice& key, void* value);

struct pair_hash {
    template <class T1, class T2>
    std::size_t operator() (const pair<T1, T2> &pair) const {
        return std::hash<T1>()(pair.first) ^ std::hash<T2>()(pair.second);
    }
};

struct CacheStat {
    enum class CacheType {
        APP,
        KERNEL
    };


    uint64_t app_cache_capacity_;

    size_t app_cache_num_ = 0;
    size_t app_cache_hit_ = 0;
    size_t kernel_cache_num_ = 0;
    size_t kernel_cache_hit_ = 0;


    CacheStat(uint64_t acc) : app_cache_capacity_(acc) {}

    void Record(CacheType type, bool hit) {
        if (type == CacheType::APP) {
            app_cache_num_ += 1;
            app_cache_hit_ += hit;
        } else {
            kernel_cache_num_ += 1;
            kernel_cache_hit_ += hit;
        }
    }

    void Clear() {
        app_cache_num_ = 0;
        app_cache_hit_ = 0;
        kernel_cache_num_ = 0;
        kernel_cache_hit_ = 0;
    }

    float Calculate(uint32_t app_miss_cost, uint32_t kernel_miss_cost) {
        if (app_cache_num_ == 0) return -1;

        float app_cache_ratio = (float) app_cache_hit_ / app_cache_num_;
        float kernel_cache_ratio = kernel_cache_num_ == 0 ? 1 : (float) kernel_cache_hit_ / kernel_cache_num_;
        float ret = (1 - app_cache_ratio) * (app_miss_cost + (1 - kernel_cache_ratio) * kernel_miss_cost);
        if (ret == 0) ret += 0.00001;
        return ret;
    }
};


class Simulator {
    friend class Adapter;
    const uint32_t k_page_size = 4096;
private:
    uint32_t num_searches_ = 5;
    uint32_t app_miss_cost_ = 5;
    uint32_t kernel_miss_cost = 100;

    uint64_t total_capacity_;
    vector<CacheStat> cache_stats_;
    Cache* app_cache_;
    Cache* kernel_cache_;

    uint32_t search_stage_ = 0;
public:
    Simulator(uint64_t total_capacity) : total_capacity_(total_capacity) {
        cache_stats_.reserve(num_searches_ + 1);
        app_cache_ = NewMultiLengthLRUCacheLevelDB(total_capacity_, num_searches_);
        kernel_cache_ = NewLRUCacheLevelDB(total_capacity_);
        for (uint32_t i = 0; i <= num_searches_; ++i) {
            uint64_t app_cache_size = total_capacity * i / num_searches_;
            cache_stats_.emplace_back(app_cache_size);
        }
    }

    ~Simulator() {
        delete app_cache_;
        delete kernel_cache_;
    }

    void IncrementSearchStage() {
        ++search_stage_;
        kernel_cache_->ChangeCapacity(total_capacity_ * (num_searches_ - search_stage_) / num_searches_);
    }

    void Simulate(uint64_t ino, uint64_t start, uint64_t size, uint64_t decompressed_size, bool heatup) {
        char cache_key_buffer[8];
        ROCKSDB_NAMESPACE::EncodeFixed32(cache_key_buffer, (uint32_t) ino);
        ROCKSDB_NAMESPACE::EncodeFixed32(cache_key_buffer + 4, (uint32_t) start);
        Slice app_key(cache_key_buffer, sizeof(cache_key_buffer));
        Cache::Handle* app_cache_handle = app_cache_->Lookup(app_key);
        if (!heatup && app_cache_handle != nullptr && (uint64_t) reinterpret_cast<LRUHandle*>(app_cache_handle)->value < search_stage_) {
            cache_stats_[search_stage_].Record(CacheStat::CacheType::APP, true);
        } else {
            cache_stats_[search_stage_].Record(CacheStat::CacheType::APP, false);
            if (app_cache_handle == nullptr) {
                app_cache_handle = app_cache_->Insert(app_key, nullptr, decompressed_size, &DeleteNullptr);
            }

            bool kernel_hit = true;
            uint32_t page_start = start / k_page_size, page_size = (start + size - 1) / k_page_size - page_start + 1;
            for (uint32_t i = page_start; i < page_start + page_size; ++i) {
                ROCKSDB_NAMESPACE::EncodeFixed32(cache_key_buffer, (uint32_t) ino);
                ROCKSDB_NAMESPACE::EncodeFixed32(cache_key_buffer + 4, (uint32_t) i);
                Slice kernel_key(cache_key_buffer, sizeof(cache_key_buffer));
                Cache::Handle* kernel_cache_handle = kernel_cache_->Lookup(kernel_key);
                if (kernel_cache_handle == nullptr) {
                    kernel_hit = false;
                    kernel_cache_handle = kernel_cache_->Insert(kernel_key, nullptr, k_page_size, &DeleteNullptr);
                }
                kernel_cache_->Release(kernel_cache_handle);
            }
            cache_stats_[search_stage_].Record(CacheStat::CacheType::KERNEL, kernel_hit);
        }
        app_cache_->Release(app_cache_handle);
    }

    std::pair<uint64_t, float> BestStat() {
        int best_index = -1;
        float best_expectation = -1;
        for (uint32_t i = 0; i <= num_searches_; ++i) {
            float expectation = cache_stats_[i].Calculate(app_miss_cost_, kernel_miss_cost);
            if (expectation < best_expectation || best_index == -1) {
                best_index = i;
                best_expectation = expectation;
            }
        }
        return std::make_pair(cache_stats_[best_index].app_cache_capacity_, best_expectation);
    }

    void ClearStats() {
        for (auto& cache_stat: cache_stats_) cache_stat.Clear();
    }

    void Clear() {
        ClearStats();
        delete app_cache_;
        delete kernel_cache_;
        app_cache_ = NewMultiLengthLRUCacheLevelDB(total_capacity_, num_searches_);
        kernel_cache_ = NewLRUCacheLevelDB(total_capacity_);
    }
};


class Adapter {
    enum class State {
        INIT = 0,
        HEATUP = 1,
        COLLECT = 2,
        STABLE = 3,
        SKETCH = 4,
        SIMULATION_HEATUP = 5,
        SIMULATION_COLLECT = 6
    };


private:
    static const uint32_t sketch_period_length_ = 2000000;
    static const uint32_t heatup_period_length_ = 300000;
    static const uint32_t stable_period_length_ = 100000;
    static constexpr float stable_tolerance_ = 0.9;
    static constexpr float jump_tolerance_ = 0.9;

    State state_ = State::INIT;
    uint32_t period_ = heatup_period_length_;
    CacheStat current_stat_;
    float stable_expectation_;
    bool wss_estimation_ = false;

    uint32_t stable_time_ = 0;
    google::dense_hash_set<pair<uint32_t, uint32_t>, pair_hash> workingset_pages_;

    Simulator simulator_;
    std::shared_ptr<ROCKSDB_NAMESPACE::Cache> real_cache_;


    void ChangeCacheCapacity(uint64_t capacity) {
        if (capacity < 1000000) capacity = 1000000;
        real_cache_->SetCapacity(capacity);
        malloc_trim(0);
    }

public:
    static Adapter* instance;

    Adapter(uint64_t total_capacity, uint64_t app_cache_capacity, std::shared_ptr<ROCKSDB_NAMESPACE::Cache> real_cache)
        : current_stat_(app_cache_capacity), stable_expectation_(0), simulator_(total_capacity), real_cache_(real_cache) {
        workingset_pages_.set_empty_key(std::make_pair(0, 0));
    }
    
    static void Init(uint64_t total_capacity, uint64_t app_cache_capacity, std::shared_ptr<ROCKSDB_NAMESPACE::Cache> real_cache) {
        assert(instance == nullptr);
        instance = new Adapter(total_capacity, app_cache_capacity, real_cache);
    }
    
    void Record(uint64_t ino, uint64_t start, uint64_t size, uint64_t decompressed_size, bool app_hit, bool kernel_hit) {
        current_stat_.Record(CacheStat::CacheType::APP, app_hit);
        if (!app_hit) current_stat_.Record(CacheStat::CacheType::KERNEL, kernel_hit);

        if (state_ == State::SIMULATION_HEATUP || state_ == State::SIMULATION_COLLECT) {
            simulator_.Simulate(ino, start, size, decompressed_size, state_ == State::SIMULATION_HEATUP);
            // if (current_stat_.app_cache_num_ % 100 == 0) {
            //     auto stat = Statistics::GetInstance();
            //     stat->ReportTime();
            //     stat->ResetAll();
            // }
        } else if (state_ == State::SKETCH) {
            uint32_t page_start = start / simulator_.k_page_size, page_size = (start + size - 1) / simulator_.k_page_size - page_start + 1;
            for (uint32_t i = page_start; i < page_start + page_size; ++i) {
                workingset_pages_.insert(std::make_pair((uint32_t) ino, (uint32_t) i));
            }
        }

        if (current_stat_.app_cache_num_ >= period_) {
            StateFunction();
        }
    }

    void StateFunction() {
        // if (simulator_.total_capacity_ == 0) return;
        float current_expectation = current_stat_.Calculate(simulator_.app_miss_cost_, simulator_.kernel_miss_cost);
        current_stat_.Clear();
        printf("State %d expectation %f app_cache %luMB\n", (int) state_, current_expectation, current_stat_.app_cache_capacity_ >> 20);
        if (simulator_.total_capacity_ == 0) return;

        if (state_ == State::INIT) {
            state_ = State::STABLE;
            period_ = stable_period_length_;
        } else if (state_ == State::HEATUP) {
            state_ = State::COLLECT;
            period_ = stable_period_length_;
        } else if (state_ == State::COLLECT) {
            stable_expectation_ = current_expectation;
            state_ = State::STABLE;
            period_ = stable_period_length_;
        } else if (state_ == State::STABLE) {
            // if (current_expectation / stable_expectation_ < stable_tolerance_) {
            //     stable_expectation_ = current_expectation;
            // }
            if (stable_expectation_ / current_expectation < stable_tolerance_) {
                stable_expectation_ = current_expectation;
                stable_time_ = 0;
                ChangeCacheCapacity(0);
                current_stat_.app_cache_capacity_ = 0;
                state_ = State::SIMULATION_HEATUP;
                period_ = heatup_period_length_;
            }

            // stable_time_ += stable_period_length_;
            // if (current_stat_.app_cache_capacity_ < simulator_.total_capacity_ / 2 && stable_time_ >= sketch_period_length_) {
            //     stable_time_ = 0;
            //     state_ = State::SKETCH;
            //     period_ = heatup_period_length_;
            // }
            stable_time_ += stable_period_length_;
            if (current_stat_.app_cache_capacity_ < simulator_.total_capacity_ / 2 && stable_time_ >= sketch_period_length_) {
                stable_time_ = 0;
                wss_estimation_ = true;
                state_ = State::SIMULATION_HEATUP;
                period_ = heatup_period_length_;
            }
        } else if (state_ == State::SKETCH) {
            int64_t workingset_size = (workingset_pages_.size() * simulator_.k_page_size) * 1.05;
            workingset_pages_.clear();
            workingset_pages_.resize(0);
            int64_t current_kernel_cache_size = simulator_.total_capacity_ - current_stat_.app_cache_capacity_;
            if (current_kernel_cache_size - workingset_size > int64_t(simulator_.total_capacity_ / simulator_.num_searches_)) {
                ChangeCacheCapacity(current_stat_.app_cache_capacity_);
                state_ = State::SIMULATION_HEATUP;
                period_ = heatup_period_length_;
            } else {
                ChangeCacheCapacity(current_stat_.app_cache_capacity_);
                state_ = State::STABLE;
                period_ = stable_period_length_;
            }
            printf("Workingset size %luMB\n", workingset_size >> 20);
        } else if (state_ == State::SIMULATION_HEATUP) {
            if (wss_estimation_) {
                wss_estimation_ = false;
                int64_t workingset_size = simulator_.kernel_cache_->TotalCharge() * 1.05;
                int64_t current_kernel_cache_size = simulator_.total_capacity_ - current_stat_.app_cache_capacity_;
                if (current_kernel_cache_size - workingset_size > int64_t(simulator_.total_capacity_ / simulator_.num_searches_)) {
                    simulator_.ClearStats();
                    simulator_.search_stage_ = 0;
                    state_ = State::SIMULATION_COLLECT;
                    period_ = stable_period_length_;
                } else {
                    simulator_.Clear();
                    ChangeCacheCapacity(current_stat_.app_cache_capacity_);
                    state_ = State::STABLE;
                    period_ = stable_period_length_;
                }
                printf("Workingset size %ldMB\n", workingset_size >> 20);
            } else {
                simulator_.ClearStats();
                simulator_.search_stage_ = 0;
                state_ = State::SIMULATION_COLLECT;
                period_ = stable_period_length_;                
            }

        } else if (state_ == State::SIMULATION_COLLECT) {
            if (simulator_.search_stage_ < simulator_.num_searches_) {
                simulator_.IncrementSearchStage();
            } else {
                std::pair<uint64_t, float> simulation_best = simulator_.BestStat();
                if (simulation_best.second / stable_expectation_ < jump_tolerance_) {
                    current_stat_.app_cache_capacity_ = simulation_best.first;
                    simulator_.Clear();
                    ChangeCacheCapacity(current_stat_.app_cache_capacity_);
                    state_ = State::HEATUP;
                    period_ = heatup_period_length_;
                    printf("Changed app cache size: %luMB, expectation %f\n", simulation_best.first >> 20, simulation_best.second);          
                } else {
                    ChangeCacheCapacity(current_stat_.app_cache_capacity_);
                    state_ = State::STABLE;
                    period_ = stable_period_length_;
                    printf("Best candidate app cache size: %luMB, expectation %f\n", simulation_best.first >> 20, simulation_best.second);
                }
            }
        }
    }
};



