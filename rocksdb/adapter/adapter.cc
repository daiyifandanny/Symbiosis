#include "adapter.h"
#include "cache/lru_cache.h"
// #include <iostream>
// #include <fstream>


// void CheckMemoryUsage() {
//   malloc_trim(0);
//   int tSize = 0, resident = 0, share = 0;
//   std::ifstream buffer("/proc/self/statm");
//   buffer >> tSize >> resident >> share;
//   buffer.close();

//   long page_size_kb = sysconf(_SC_PAGE_SIZE) / 1024; // in case x86-64 is configured to use 2MB pages
//   double rss = resident * page_size_kb;
//   std::cout << "RSS - " << rss << " kB\n";

//   double shared_mem = share * page_size_kb;
//   std::cout << "Shared Memory - " << shared_mem << " kB\n";

//   std::cout << "Private Memory - " << rss - shared_mem << "kB\n";
// }


uint64_t ino;
uint32_t bno;
uint32_t bno_max;
bool app_hit;
bool kernel_hit;
uint64_t app_size;
uint64_t kernel_size;


namespace Rebirth {

std::ofstream debug_output("debug.out");

void DeleteNullptr(const Slice& key, void* value) {};

Adapter* Adapter::instance = nullptr;

void Adapter::StateFunction() {
    // if (simulator_.total_capacity_ == 0) return;
    float current_expectation = current_stat_.Calculate(simulator_.app_miss_cost_, simulator_.kernel_miss_cost);
    current_stat_.Clear();
    auto app_cache_ptr = reinterpret_cast<ROCKSDB_NAMESPACE::LRUCache*>(real_app_cache_.get());
    auto kernel_cache_ptr = reinterpret_cast<ROCKSDB_NAMESPACE::LRUCache*>(real_kernel_cache_.get());
    printf("State %d expectation %f app_cache %luMB app_cache_num %u kernel_cache %luMB kernel_cache_num %u\n", (int) state_, current_expectation,
            app_cache_ptr->shards_[0].usage_ >> 20, app_cache_ptr->shards_[0].table_.elems_,
            kernel_cache_ptr->shards_[0].usage_ >> 20, kernel_cache_ptr->shards_[0].table_.elems_);
    if (simulator_.total_capacity_ == 0) {
        // static int trim_counter = 0;
        // if (++trim_counter % 10 == 0) {
        //     malloc_trim(0);
        // }
        return;
    }

    if (state_ == State::INIT) {
        // simulator_.compression_ratio = float(compressed_size_) / decompressed_size_;
        state_ = State::SIMULATION_HEATUP;
        period_ = heatup_period_length_;
    } else if (state_ == State::HEATUP) {
        state_ = State::COLLECT;
        period_ = stable_period_length_;
    } else if (state_ == State::COLLECT) {
        stable_expectation_ = current_expectation;
        stablized = false;
        state_ = State::STABLE;
        period_ = stable_period_length_;
        // fprintf(output_file, "%u Stable\n", current_ops);
    } else if (state_ == State::STABLE) {
        // static int trim_counter = 0;
        // if (++trim_counter % 20 == 0) {
        //     malloc_trim(0);
        // }

        if (!stablized) {
            if (current_expectation < stable_expectation_) {
                stable_expectation_ = current_expectation;
            } else {
                stablized = true;
            }
        }

        if (stablized && (stable_expectation_ / current_expectation < stable_tolerance_ || 
            current_expectation / stable_expectation_ < stable_tolerance_) &&
            abs(current_expectation - stable_expectation_) > 0.5) {
            // CheckMemoryUsage();
            bool change_cache_size = false;
            // if (stable_expectation_ < current_expectation) {
            //     ChangeAppCacheSize(default_app_cache_size_);
            //     current_stat_.app_cache_capacity_ = default_app_cache_size_;
            //     change_cache_size = true;
            // }
            stable_expectation_ = current_expectation;
            stable_time_ = 0;
            simulator_.Init();
            state_ = State::SIMULATION_HEATUP;
            period_ = heatup_period_length_;
#ifdef MULTI_GHOST
            period_ *= 1.5;
#endif
            if (change_cache_size) {
                // fprintf(output_file, "%u Simulation Change\n", current_ops);
            } else {
                // fprintf(output_file, "%u Simulation Unchange\n", current_ops);
            }
            // CheckMemoryUsage();
        } else {
            stable_time_ += stable_period_length_;
            if (float(current_stat_.app_cache_capacity_) / simulator_.total_capacity_ < 0.8 && stable_time_ >= sketch_period_length_) {
                stable_time_ = 0;
                // wss_estimation_ = true;
                simulator_.Init();
                state_ = State::SIMULATION_HEATUP;
                period_ = heatup_period_length_;
#ifdef MULTI_GHOST
                period_ *= 1.5;
#endif
                // fprintf(output_file, "%u Simulation Unchange\n", current_ops);
            }
        }

        // stable_time_ += stable_period_length_;
        // if (current_stat_.app_cache_capacity_ < simulator_.total_capacity_ / 2 && stable_time_ >= sketch_period_length_) {
        //     stable_time_ = 0;
        //     state_ = State::SKETCH;
        //     period_ = heatup_period_length_;
        // }

    } else if (state_ == State::SKETCH) {
        assert(false);
        // int64_t workingset_size = (workingset_pages_.size() * simulator_.k_page_size * simulator_.space_sample_length) * 1.05;
        // workingset_pages_.clear();
        // workingset_pages_.resize(0);
        // int64_t current_kernel_cache_size = simulator_.total_capacity_ - current_stat_.app_cache_capacity_;
        // if (current_kernel_cache_size - workingset_size > int64_t(simulator_.total_capacity_ / simulator_.num_searches_)) {
        //     db_->ChangeCacheCapacity(current_stat_.app_cache_capacity_);
        //     state_ = State::SIMULATION_HEATUP;
        //     period_ = heatup_period_length_;
        // } else {
        //     db_->ChangeCacheCapacity(current_stat_.app_cache_capacity_);
        //     state_ = State::STABLE;
        //     period_ = stable_period_length_;
        // }
        // printf("Workingset size %luMB\n", workingset_size >> 20);
    } else if (state_ == State::SIMULATION_HEATUP) {
        if (wss_estimation_) {
            assert(false);
            // wss_estimation_ = false;
            // int64_t wss = simulator_.kernel_cache_->TotalCharge();
            // if (int64_t(current_wss_ - wss) > int64_t(simulator_.total_capacity_ / simulator_.num_searches_)) {
            //     simulator_.ClearStats();
            //     simulator_.search_stage_ = -1;
            //     simulator_.IncrementSearchStage();
            //     current_wss_ = wss;
            //     // simulator_.grouping_filter_.clear();
            //     state_ = State::SIMULATION_COLLECT;
            //     period_ = stable_period_length_;
            // } else {
            //     simulator_.Clear();
            //     // simulator_.grouping_filter_.clear();
            //     db_->ChangeCacheCapacity(current_stat_.app_cache_capacity_);
            //     state_ = State::STABLE;
            //     period_ = stable_period_length_;
            // }
            // printf("Workingset size %ldMB\n", wss >> 20);
        } else {
            simulator_.ClearStats();
            simulator_.search_stage_ = -1;
            simulator_.IncrementSearchStage();
            // CheckMemoryUsage();
            // simulator_.grouping_filter_.clear();
            // current_wss_ = simulator_.app_cache_->TotalCharge();
            // simulator_.app_cache_->Dump();
            state_ = State::SIMULATION_COLLECT;
            period_ = stable_period_length_;                
        }

    } else if (state_ == State::SIMULATION_COLLECT) {
        if (simulator_.search_stage_ < simulator_.num_searches_) {
            simulator_.IncrementSearchStage();
        } else {
            // CheckMemoryUsage();
            std::pair<uint64_t, float> simulation_best = simulator_.BestStat(stable_period_length_);
            simulator_.Clear();
            // fprintf(output_file, "%u Done\n", current_ops);
            if (simulation_best.first != current_stat_.app_cache_capacity_ && 
                simulation_best.second / current_expectation < jump_tolerance_) {
                current_stat_.app_cache_capacity_ = simulation_best.first;
                ChangeAppCacheSize(current_stat_.app_cache_capacity_);
                state_ = State::HEATUP;
                period_ = heatup_period_length_ * 3;
                printf("Changed app cache size: %luMB, expectation %f, current %f\n", simulation_best.first >> 20, simulation_best.second, current_expectation);          
            } else {
                // ChangeAppCacheSize(current_stat_.app_cache_capacity_);
                state_ = State::HEATUP;
                period_ = stable_period_length_;
                printf("Best candidate app cache size: %luMB, expectation %f, current %f\n", simulation_best.first >> 20, simulation_best.second, current_expectation);
            }
        }
    }
}

}
