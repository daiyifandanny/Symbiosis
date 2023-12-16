#include "leveldb/cache.h"
#include "leveldb/db.h"
#include "util/coding.h"
#include <vector>
#include <limits>
#include "stats.h"
#include <malloc.h>
#include <algorithm>
#include <x86intrin.h>
#include "table/block.h"
#include "util/global.h"
#include "leveldb/env.h"


using std::vector;
using std::pair;
using namespace leveldb;


// #define MULTI_GHOST


class Adapter;

void DeleteNullptr(const Slice& key, void* value);

struct CacheStat {
    enum class CacheType {
        APP,
        KERNEL
    };


    uint64_t app_cache_capacity_;

    uint32_t app_cache_num_ = 0;
    uint32_t app_cache_miss_ = 0;
    uint32_t kernel_cache_num_ = 0;
    uint32_t kernel_cache_miss_ = 0;

    CacheStat(uint64_t acc) : app_cache_capacity_(acc) {}

    void Record(CacheType type, bool hit) {
        if (type == CacheType::APP) {
            app_cache_num_ += 1;
            app_cache_miss_ += !hit;
        } else {
            kernel_cache_num_ += 1;
            kernel_cache_miss_ += !hit;
        }
    }

    void Clear() {
        app_cache_num_ = 0;
        app_cache_miss_ = 0;
        kernel_cache_num_ = 0;
        kernel_cache_miss_ = 0;
    }

    float Calculate(uint32_t app_miss_cost, uint32_t kernel_miss_cost) {
        if (app_cache_num_ == 0) return -1;
        Print();

        float app_cache_miss_ratio = std::min(float(app_cache_miss_) / app_cache_num_, float(1));
        float kernel_cache_miss_ratio = kernel_cache_num_ == 0 ? 0 : float(kernel_cache_miss_) / kernel_cache_num_;
        float ret = app_cache_miss_ratio * (app_miss_cost + kernel_cache_miss_ratio * kernel_miss_cost);
        if (ret == 0) ret += 0.00001;
        return ret;
    }

    void Print() {
        printf("%u %u %u %u\n", app_cache_num_, app_cache_miss_, kernel_cache_num_, kernel_cache_miss_);
    }
};


class Simulator {
    friend class Adapter;
    static const uint32_t k_page_shift = 12;
    static const uint32_t k_page_size = 1 << k_page_shift;
    static const uint32_t k_ino_factor = 12;
private:
    static const uint32_t num_searches_ = 8;
    static const uint32_t app_miss_cost_ = 3;
    static const uint32_t kernel_miss_cost = 16;
    static const uint32_t sampling_factor = 6;
    static const uint32_t grouping_factor = 5;

    uint64_t total_capacity_;
    vector<CacheStat> cache_stats_;
    MultiLengthLRUCache* app_cache_ = nullptr;
#ifdef MULTI_GHOST
    LRUCache* kernel_caches_[num_searches_ + 1];
#else
    LRUCache* kernel_cache_ = nullptr;
#endif
    uint32_t search_stage_ = 0;
    float compression_ratio = 0.5;
public:
    Simulator(uint64_t total_capacity) : total_capacity_(total_capacity) {
        if (total_capacity == 0) {
            return;
        }
        // num_searches_ = std::min(uint32_t(total_capacity / 20000000) * 256 / space_sample_length
        //                         , num_searches_);
        cache_stats_.resize(num_searches_ + 1, {0});
        // grouping_filter_ = new google::dense_hash_set<uint32_t>;
        // grouping_filter_->set_empty_key(UINT32_MAX);
        // kernel_cache_ = new LRUCache();
        // app_cache_ = new MultiLengthLRUCache(num_searches_);
        // kernel_cache_->SetCapacity(total_capacity_);
        // app_cache_->SetCapacity(total_capacity_);
        // kernel_cache_ = NewLRUCache(total_capacity_);
        // app_cache_ = NewMultiLengthLRUCache(total_capacity_, num_searches_);
        for (uint32_t i = 0; i <= num_searches_; ++i) {
            uint64_t app_cache_size = total_capacity * i / num_searches_;
            cache_stats_[i].app_cache_capacity_ = app_cache_size;
        }
        // Clear();
    }

    ~Simulator() {
        delete app_cache_;
#ifdef MULTI_GHOST
        for (uint32_t i = 0; i <= num_searches_; ++i) {
        auto& kernel_cache_ = kernel_caches_[i];
#endif
        delete kernel_cache_;
#ifdef MULTI_GHOST
        }
#endif
    }

    void PrintSizes() {
#ifdef MULTI_GHOST
        for (uint32_t i = 0; i <= num_searches_; ++i) {
        auto& kernel_cache_ = kernel_caches_[i];
#endif
        printf("app_cache_size %lu kernel_cache_size %lu\n", app_cache_->TotalCharge(), kernel_cache_->TotalCharge());
#ifdef MULTI_GHOST
        }
#endif
    }

    void IncrementSearchStage() {
#ifdef MULTI_GHOST
        search_stage_ = num_searches_;
#else
        ++search_stage_;
        kernel_cache_->ChangeCapacity(total_capacity_ * (num_searches_ - search_stage_) / num_searches_ + 10000000, true);
#endif
        PrintSizes();
    }

    static inline uint32_t SamplingBits(uint32_t orig) {
        return orig & ((1 << sampling_factor) - 1);
    }

    static inline uint32_t CRCHash(uint32_t key) {
        return _mm_crc32_u32(811, key);
    }

    void Simulate(uint64_t hash, bool record) {
        if (record && SamplingBits(hash) == 0) 
            cache_stats_[search_stage_].Record(CacheStat::CacheType::APP, true);
    }

    void Simulate(uint64_t ino, uint64_t start, uint64_t size, Iterator* iter, 
                    uint64_t decompressed_size, bool heatup, bool record) {
        Block::Iter* iiter = static_cast<Block::Iter*>(iter);
        uint32_t app_index_current = iiter->GetIndex();
        uint32_t app_index_max = iiter->GetMaxIndex();

        uint32_t group_index = ((ino << k_ino_factor) + app_index_current) >> grouping_factor;
        uint32_t grouping_hash = CRCHash(group_index);
        if (SamplingBits(grouping_hash) != 0) {
            return;
        }

        bool inserted = true;
        uint32_t app_index_start = app_index_current;
        uint32_t app_index_end = app_index_current + 1;
        if (heatup && !app_cache_->Full()) {
            app_index_start = app_index_current >> grouping_factor << grouping_factor;
            app_index_end = std::min(app_index_max + 1, ((app_index_current >> grouping_factor) + 1) << grouping_factor);
        }

        bool kernel_processed = false;
        for (uint32_t app_index = app_index_start; app_index < app_index_end; ++app_index) {
            char cache_key_buffer[4];
            uint32_t uint_app_key = (uint32_t(ino) << k_ino_factor) + uint32_t(app_index);
            EncodeFixed32(cache_key_buffer, uint_app_key);
            assert(sizeof(cache_key_buffer) == 4);
            Slice app_key(cache_key_buffer, sizeof(cache_key_buffer));
            uint32_t app_hash = CRCHash(uint_app_key);

            Cache::Handle* app_cache_handle = app_cache_->Lookup(app_key, app_hash);
            if (app_cache_handle != nullptr) {
                inserted = false;
                app_index_end = app_index;
            }
#ifdef MULTI_GHOST
            for (uint32_t search_stage_ = 0; search_stage_ <= num_searches_; ++search_stage_) {
            auto& kernel_cache_ = kernel_caches_[search_stage_];
            if ((!heatup || kernel_cache_->Full()) && app_cache_handle != nullptr && reinterpret_cast<LRUHandle*>(app_cache_handle)->rank < search_stage_) {
#else
            if (!heatup && app_cache_handle != nullptr && reinterpret_cast<LRUHandle*>(app_cache_handle)->rank < search_stage_) {
#endif
                if (record) cache_stats_[search_stage_].Record(CacheStat::CacheType::APP, true);
#ifdef MULTI_GHOST
                if (search_stage_ == num_searches_) {
#endif
                app_cache_->Release(app_cache_handle);
#ifdef MULTI_GHOST
                }
#endif
            } else {
                if (record) cache_stats_[search_stage_].Record(CacheStat::CacheType::APP, false);
#ifdef MULTI_GHOST
                if (search_stage_ == num_searches_) {
#endif
                if (app_cache_handle == nullptr) {
                    app_cache_handle = app_cache_->Insert(app_key, app_hash, nullptr,
                                                            decompressed_size << sampling_factor, &DeleteNullptr);
                }
                app_cache_->Release(app_cache_handle);
#ifdef MULTI_GHOST
                }
#endif

                if (kernel_processed) continue;
#ifdef MULTI_GHOST
                if (search_stage_ == num_searches_) {
#endif
                kernel_processed = true;
#ifdef MULTI_GHOST
                }
#endif

                bool kernel_hit = true;
                uint32_t byte_start = start;
                uint32_t byte_end = start + size - 1;
                uint32_t index_start = app_index_current >> grouping_factor << grouping_factor;
                uint32_t index_end = std::min(app_index_max + 1, ((app_index_current >> grouping_factor) + 1) << grouping_factor);   
                if (heatup && inserted && !kernel_cache_->Full()) {
                    iiter->SeekToRestartPoint(index_start);
                    iiter->Next();
                    BlockHandle handle;
                    Slice input = iiter->value();
                    handle.DecodeFrom(&input);
                    byte_start = handle.offset();

                    iiter->SeekToRestartPoint(index_end - 1);
                    iiter->Next();
                    input = iiter->value();
                    handle.DecodeFrom(&input);
                    byte_end = handle.offset() + handle.size() - 1;
                }

                uint32_t page_start = byte_start >> k_page_shift;
                uint32_t page_end = (byte_end >> k_page_shift) + 1;
                for (uint32_t i = page_start; i < page_end; i += 1) {
#ifdef MULTI_GHOST
                    char cache_key_buffer[4];
#endif
                    uint32_t uint_kernel_key = (uint32_t(ino) << k_ino_factor) + i;
                    EncodeFixed32(cache_key_buffer, uint_kernel_key);
                    Slice kernel_key(cache_key_buffer, sizeof(cache_key_buffer));
                    uint32_t kernel_hash = CRCHash(uint_kernel_key);

                    Cache::Handle* kernel_cache_handle = kernel_cache_->Lookup(kernel_key, kernel_hash);
                    if (kernel_cache_handle == nullptr) {
                        kernel_hit = false;
                        float size_factor = sampling_factor == 0 ? 1 :
                                            (size * (index_end - index_start)) / 
                                            (size * (index_end - index_start) + 2 * float(k_page_size));
                                            // (size * (1 << grouping_factor) + float(k_page_size) * size / decompressed_size);
                        kernel_cache_handle = kernel_cache_->Insert(kernel_key, kernel_hash, nullptr, (k_page_size << sampling_factor) * size_factor, &DeleteNullptr);
                    }
                    kernel_cache_->Release(kernel_cache_handle);
                }
                if (record) cache_stats_[search_stage_].Record(CacheStat::CacheType::KERNEL, kernel_hit);
            }
#ifdef MULTI_GHOST
            }
#endif
        }
    }

    std::pair<uint64_t, float> BestStat(uint32_t period) {
        int best_index = -1;
        float best_expectation;
        printf("Simulation Result\n");
        for (uint32_t i = 0; i <= num_searches_; ++i) {
            cache_stats_[i].app_cache_num_ = (period) >> sampling_factor;
            float expectation = cache_stats_[i].Calculate(app_miss_cost_, kernel_miss_cost);
            printf("Search %u app_cache %luMB expectation %f\n", i, cache_stats_[i].app_cache_capacity_ >> 20, expectation);
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

    void Init() {
#ifdef MULTI_GHOST
        for (uint32_t i = 0; i <= num_searches_; ++i) {
        auto& kernel_cache_ = kernel_caches_[i];
#endif
        kernel_cache_ = new LRUCache();
#ifdef MULTI_GHOST
        kernel_cache_->SetCapacity(total_capacity_ * (num_searches_ - i) / num_searches_);
#else
        kernel_cache_->SetCapacity(total_capacity_);
#endif
#ifdef MULTI_GHOST
        }
#endif
        app_cache_ = new MultiLengthLRUCache(num_searches_);
        app_cache_->SetCapacity(total_capacity_);
        // kernel_cache_ = NewLRUCache(total_capacity_);
        // app_cache_ = NewMultiLengthLRUCache(total_capacity_, num_searches_);
        search_stage_ = 0;
    }

    void Clear() {
        ClearStats();
        delete app_cache_;
#ifdef MULTI_GHOST
        for (uint32_t i = 0; i < num_searches_; ++i) {
        auto& kernel_cache_ = kernel_caches_[i];
#endif
        delete kernel_cache_;
#ifdef MULTI_GHOST
        }
#endif
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
    static const uint32_t sketch_period_length_ = 10000000;
    static const uint32_t heatup_period_length_ = 400000;
    static const uint32_t stable_period_length_ = 200000;
    static constexpr float stable_tolerance_ = 0.9;
    static constexpr float jump_tolerance_ = 0.9;
    static const uint64_t default_app_cache_size_ = 0;

    uint64_t decompressed_size_ = 0;
    uint64_t compressed_size_ = 0;
    bool enable_multi_simulation = true;

    State state_ = State::STABLE;
    uint32_t period_ = stable_period_length_;
    CacheStat current_stat_;
    float stable_expectation_;
    bool wss_estimation_ = false;
    bool stablized = true;
    bool enable_simulation = true;

    uint32_t stable_time_ = 0;
    uint64_t current_wss_ = 0;

    Simulator simulator_;
    DB* db_;
public:
    static Adapter* instance;

    Adapter(uint64_t total_capacity, uint64_t app_cache_capacity, DB* db)
        : current_stat_(default_app_cache_size_), stable_expectation_(0), simulator_(total_capacity), db_(db) {
    }
    
    static void Init(uint64_t total_capacity, uint64_t app_cache_capacity, DB* db) {
        assert(instance == nullptr);
        instance = new Adapter(total_capacity, app_cache_capacity, db);
        if (app_cache_capacity == 0) db->ChangeCacheCapacity(default_app_cache_size_);
    }

    void DisableMultiSimulation() {
        enable_multi_simulation = false;
    }
    
    void Record(uint64_t ino, uint64_t start, uint64_t size, Iterator* iiter, 
                uint64_t decompressed_size, bool app_hit, bool kernel_hit) {
        // if (simulator_.total_capacity_ == 0) return;
        current_stat_.Record(CacheStat::CacheType::APP, app_hit);
        if (!app_hit) current_stat_.Record(CacheStat::CacheType::KERNEL, kernel_hit);
        // Statistics* instance = Statistics::GetInstance();

        if (current_stat_.app_cache_num_ >= period_) {
            StateFunction();
            return;
        }
        if (simulator_.total_capacity_ == 0) return;

        // if (state_ == State::INIT) {
        //     decompressed_size_ += decompressed_size;
        //     compressed_size_ += size;
        // }

        if (state_ == State::SIMULATION_HEATUP || state_ == State::SIMULATION_COLLECT) {
            bool record = state_ == State::SIMULATION_COLLECT && current_stat_.app_cache_num_ >= 0;
            if (ino == 0) {
                simulator_.Simulate(start, record);
            } else {
                // instance->StartTimer(1);
                simulator_.Simulate(ino, start, size, iiter, decompressed_size, 
                                    state_ == State::SIMULATION_HEATUP, record);
                // if (current_stat_.app_cache_num_ % 100 == 0) {
                //     auto stat = Statistics::GetInstance();
                //     stat->ReportTime();
                //     stat->ResetAll();
                // }
                // instance->PauseTimer(1);                
            }
        } else if (state_ == State::SKETCH) {
            assert(false);
            // uint32_t page_start = start / simulator_.k_page_size, page_size = (start + size - 1) / simulator_.k_page_size - page_start + 1;
            // for (uint64_t i = simulator_.Align(page_start); i < page_start + page_size; i += simulator_.space_sample_length) {
            //     workingset_pages_.insert(std::make_pair((uint32_t) ino, (uint32_t) i));
            // }
        }
    }

    void StateFunction();
};
