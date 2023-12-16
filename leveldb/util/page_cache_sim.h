#include <tsl/ordered_map.h>
#include <cmath>
#include <unordered_map>
#include "stats.h"
#include "leveldb/cache.h"
#include "util/coding.h"
#include "util/hash.h"


using std::pair;
using namespace leveldb;


class PageCacheSimulator;

struct pair_hash {
    template <class T1, class T2>
    std::size_t operator() (const pair<T1, T2> &pair) const {
        return std::hash<T1>()(pair.first) ^ std::hash<T2>()(pair.second);
    }
};

void DeletePCItem(const Slice& key, void* value);


struct PageCacheItem {
    bool referenced = false;
    bool readahead_mark;

    PageCacheItem(bool marked) : readahead_mark(marked) {};
};

class PageCache {
public:
    using KeyType = pair<uint64_t, uint64_t>;

private:
    static const uint32_t default_shift = 4096;
    static const uint32_t min_capacity = 256;
    static const uint32_t min_eviction = 32;

    tsl::ordered_map<KeyType, PageCacheItem, pair_hash> active_queue_;
    tsl::ordered_map<KeyType, PageCacheItem, pair_hash> inactive_queue_;
    tsl::ordered_map<KeyType, uint64_t, pair_hash> shadow_entries_;
    uint64_t capacity_;
    uint64_t size_ = 0;
    uint64_t eviction_count_ = 0;
    uint64_t activation_count_ = 0;
    uint32_t shift_ = 12;


    uint64_t Size() {
        size_ = active_queue_.size() + inactive_queue_.size();
        printf("%lu\n", size_);
        return active_queue_.size() + inactive_queue_.size();
    }

    uint64_t RefaultCounter() {return eviction_count_ + activation_count_;}
    
    uint32_t GetScanCount(const tsl::ordered_map<pair<uint64_t, uint64_t>, PageCacheItem, pair_hash>& target) {
        uint32_t count = std::max((uint32_t) target.size() >> shift_, 1U);
        while (count < min_eviction) {
            count <<= 1;
            shift_ -= 1;
        }
        return count;
    }

    void InsertActive(const KeyType& key, const PageCacheItem& value) {
        activation_count_ += 1;
        active_queue_.insert({key, value});
    }

    void InsertInactive(const KeyType& key, const PageCacheItem& value) {inactive_queue_.insert({key, value});}

    uint32_t ShrinkActive() {
        uint32_t shrinked = std::min((uint64_t) GetScanCount(active_queue_), active_queue_.size());
        for (uint32_t i = 0; i < shrinked; ++i) {
            inactive_queue_.insert(active_queue_.back());
            active_queue_.pop_back();
        }
        return shrinked;
    }

    void Ref(const KeyType& key) {
        auto iter = active_queue_.find(key);
        if (iter != active_queue_.end()) {
            iter.value().referenced = true;
            return;
        }
        iter = inactive_queue_.find(key);
        if (iter != inactive_queue_.end()) {
            if (iter.value().referenced) {
                iter.value().referenced = false;
                active_queue_.insert({iter.key(), iter.value()});
                inactive_queue_.erase(iter);
            } else {
                iter.value().referenced = true;
            }
        }
    }

    uint32_t Evict() {
        uint32_t capacity_gb = capacity_ >> 18;
        float ratio = capacity_gb == 0 ? 1 : sqrt(capacity_gb * 10);
        if (inactive_queue_.size() * ratio < active_queue_.size()) ShrinkActive();
        assert(inactive_queue_.size() > min_eviction);

        uint32_t scan_count = GetScanCount(inactive_queue_);
        for (uint32_t i = 0; i < scan_count; ++i) {
            auto back = inactive_queue_.back();
            shadow_entries_.insert({back.first, RefaultCounter() + active_queue_.size()});
            if (shadow_entries_.size() >= capacity_) shadow_entries_.pop_back();
            inactive_queue_.pop_back();
        }
        return scan_count;
    }

public:
    PageCache(uint64_t capacity) : capacity_(capacity) {};

    void ChangeCapacity(uint64_t capacity, bool delta) {
        if (delta) capacity_ += capacity;
        else capacity_ = capacity;
        assert(capacity_ >= min_capacity);

        while (Size() >= capacity_) Evict();
        while (shadow_entries_.size() >= capacity_) shadow_entries_.pop_back();
        shift_ = default_shift;
    }
    
    PageCacheItem* Get(const KeyType& key, bool reference) {
        auto iter = active_queue_.find(key);
        if (iter != active_queue_.end()) {
            if (reference) {
                iter.value().referenced = true;
            }
            return &iter.value();
        }

        iter = inactive_queue_.find(key);
        if (iter != inactive_queue_.end()) {
            if (reference) {
                if (iter.value().referenced) {
                    iter.value().referenced = false;
                    active_queue_.insert({iter.key(), iter.value()});
                    inactive_queue_.erase(iter);
                } else {
                    iter.value().referenced = true;
                }                
            }
            return &iter.value();
        }

        return nullptr;
    }

    bool Put(const KeyType& key, bool readahead_marked) {
        if (Get(key, false) != nullptr) return false;

        bool eviction_triggered = false;
        while (Size() >= capacity_) {
            Evict();
            eviction_triggered = true;
        }

        PageCacheItem value(readahead_marked);
        auto iter = shadow_entries_.find(key);
        if (iter != shadow_entries_.end()) {
            if (RefaultCounter() <= iter.value()) InsertActive(key, value);
            else InsertInactive(key, value);
            shadow_entries_.erase(iter);
        } else {
            InsertInactive(key, value);
        }
        return eviction_triggered;
    }
};

class PageCache2 {
public:
    using KeyType = pair<uint64_t, uint64_t>;

private:
    static const uint32_t default_shift = 4096;
    static const uint32_t min_capacity = 256;
    static const uint32_t min_eviction = 32;

    LRUCache* active_queue_;
    LRUCache* inactive_queue_;
    // LRUCache* shadow_entries_;
    uint64_t capacity_;
    uint64_t size_ = 0;
    uint64_t eviction_count_ = 0;
    uint64_t activation_count_ = 0;
    uint32_t shift_ = 12;


    uint64_t Size() {
        // size_ = active_queue_->TotalCharge() + inactive_queue_->TotalCharge();
        // printf("%lu\n", size_);
        return active_queue_->TotalCharge() + inactive_queue_->TotalCharge();
    }

    uint64_t RefaultCounter() {return eviction_count_ + activation_count_;}
    
    uint32_t GetScanCount(LRUCache* target) {
        uint32_t count = std::max((uint32_t) target->TotalCharge() >> shift_, 1U);
        while (count < min_eviction) {
            count <<= 1;
            shift_ -= 1;
        }
        return count;
    }

    void InsertActive(const KeyType& key, PageCacheItem* value) {
        activation_count_ += 1;
        char cache_key_buffer[16];
        EncodeFixed64(cache_key_buffer, key.first);
        EncodeFixed64(cache_key_buffer + 8, key.second);\
        Slice k(cache_key_buffer, sizeof(cache_key_buffer));
        auto cache_handle = active_queue_->Insert(k, Hash(k.data(), k.size(), 0), (void*) value, 1, &DeletePCItem);
        active_queue_->Release(cache_handle);
    }

    void InsertInactive(const KeyType& key, PageCacheItem* value) {
        char cache_key_buffer[16];
        EncodeFixed64(cache_key_buffer, key.first);
        EncodeFixed64(cache_key_buffer + 8, key.second);\
        Slice k(cache_key_buffer, sizeof(cache_key_buffer));
        auto cache_handle = inactive_queue_->Insert(k, Hash(k.data(), k.size(), 0), (void*) value, 1, &DeletePCItem);
        inactive_queue_->Release(cache_handle);
    }

    uint32_t ShrinkActive() {
        uint32_t shrinked = std::min((uint64_t) GetScanCount(active_queue_), active_queue_->TotalCharge());
        for (uint32_t i = 0; i < shrinked; ++i) {
            LRUHandle* back = active_queue_->Back();
            auto cache_handle = inactive_queue_->Insert((Slice) {back->key_data, back->key_length}, 
                back->hash, back->value, back->charge, back->deleter);
            inactive_queue_->Release(cache_handle);
            back->value = nullptr;
            active_queue_->PopBack();
        }
        return shrinked;
    }

    uint32_t Evict() {
        uint32_t capacity_gb = capacity_ >> 18;
        float ratio = capacity_gb == 0 ? 1 : sqrt(capacity_gb * 10);
        if (inactive_queue_->TotalCharge() * ratio < active_queue_->TotalCharge()) ShrinkActive();
        assert(inactive_queue_->TotalCharge() > min_eviction);

        uint32_t scan_count = GetScanCount(inactive_queue_);
        for (uint32_t i = 0; i < scan_count; ++i) {
            // auto back = inactive_queue_.back();
            // shadow_entries_.insert({back.first, RefaultCounter() + active_queue_.size()});
            // if (shadow_entries_.size() >= capacity_) shadow_entries_.pop_back();
            inactive_queue_->PopBack();
        }
        return scan_count;
    }

public:
    PageCache2(uint64_t capacity) : 
        capacity_(capacity), active_queue_(new LRUCache()), inactive_queue_(new LRUCache()) {
        active_queue_->SetCapacity(capacity_);
        inactive_queue_->SetCapacity(capacity_);
    }

    ~PageCache2() {
        delete active_queue_;
        delete inactive_queue_;
    }

    void Clear() {
        delete active_queue_;
        delete inactive_queue_;
        active_queue_ = new LRUCache();
        inactive_queue_ = new LRUCache();
        active_queue_->SetCapacity(capacity_);
        inactive_queue_->SetCapacity(capacity_);
    }

    void ChangeCapacity(uint64_t capacity, bool delta) {
        if (delta) capacity_ += capacity;
        else capacity_ = capacity;
        assert(capacity_ >= min_capacity);

        while (Size() >= capacity_) Evict();
        active_queue_->SetCapacity(capacity_);
        inactive_queue_->SetCapacity(capacity_);
        // while (shadow_entries_.size() >= capacity_) shadow_entries_.pop_back();
        shift_ = default_shift;
    }
    
    PageCacheItem* Get(const KeyType& key, bool reference) {
        char cache_key_buffer[16];
        EncodeFixed64(cache_key_buffer, key.first);
        EncodeFixed64(cache_key_buffer + 8, key.second);\
        Slice k(cache_key_buffer, sizeof(cache_key_buffer));
        auto hash = Hash(k.data(), k.size(), 0);
        auto cache_handle = active_queue_->Lookup(k, hash, false);
        if (cache_handle != nullptr) {
            auto value = reinterpret_cast<PageCacheItem*>(reinterpret_cast<LRUHandle*>(cache_handle)->value);
            if (reference) {
                value->referenced = true;
            }
            active_queue_->Release(cache_handle);
            return value;
        }

        cache_handle = inactive_queue_->Lookup(k, hash, false);
        if (cache_handle != nullptr) {
            auto value = reinterpret_cast<PageCacheItem*>(reinterpret_cast<LRUHandle*>(cache_handle)->value);
            if (reference) {
                if (value->referenced) {
                    value->referenced = false;
                    auto next_handle = active_queue_->Insert(k, hash, value, 1, &DeletePCItem);
                    active_queue_->Release(next_handle);
                    reinterpret_cast<LRUHandle*>(cache_handle)->value = nullptr;
                    inactive_queue_->Erase(k, hash);
                } else {
                    value->referenced = true;
                }
            }
            inactive_queue_->Release(cache_handle);
            return value;
        }

        return nullptr;
    }

    bool Put(const KeyType& key, bool readahead_marked) {
        if (Get(key, false) != nullptr) return false;

        bool eviction_triggered = false;
        while (Size() >= capacity_) {
            Evict();
            eviction_triggered = true;
        }

        PageCacheItem* value = new PageCacheItem(readahead_marked);
        InsertInactive(key, value);
        // auto iter = shadow_entries_.find(key);
        // if (iter != shadow_entries_.end()) {
        //     if (RefaultCounter() <= iter.value()) InsertActive(key, value);
        //     else InsertInactive(key, value);
        //     shadow_entries_.erase(iter);
        // } else {
        //     InsertInactive(key, value);
        // }
        return eviction_triggered;
    }
};



class Readahead {
    friend class PageCacheSimulator;
private:
    int prev_index_ = -1;
    int start_index_ = -1;
    int lookahead_index_ = -1;
    int max_readahead_ = 32;
    int current_readahead_ = -1;
    PageCacheSimulator* page_cache_ = nullptr;


    void Clear() {
        start_index_ = -1;
        lookahead_index_ = -1;
        current_readahead_ = -1;
    }

    int InitRaValue(int size) {
        int new_size = (int) pow(2, ceil(log(size)));
        if (new_size <= max_readahead_ / 32) new_size *= 4;
        else if (new_size <= max_readahead_ / 4) new_size *= 2;
        else new_size = max_readahead_;
        return new_size;
    }

    void Reset(int target, bool init = true) {
        if (init) current_readahead_ = InitRaValue(1);
        start_index_ = target;
        lookahead_index_ = target + (current_readahead_ >=4 ? current_readahead_ / 4 : 1);
    }

    int NextRaValue() {
        int next_value = current_readahead_;
        if (next_value <  max_readahead_ / 16) next_value *= 4;
        else next_value = std::min(max_readahead_, next_value *= 2);
        return next_value;
    }

    void AssignRaValue(int value) {current_readahead_ = std::min(value, max_readahead_);}

public:
    Readahead(PageCacheSimulator* page_cache) : page_cache_(page_cache) {};
    void Update(PageCache::KeyType key, int size, bool mark_hit);
};


class PageCacheSimulator {
private:
    PageCache2 page_cache_;
    std::unordered_map<uint64_t, Readahead> readahead_structs_;

public:
    PageCacheSimulator(uint64_t capacity) : page_cache_(capacity) {}

    void Clear() {
        page_cache_.Clear();
        readahead_structs_.clear();
    }

    int FindClosestHoleBefore(PageCache::KeyType key, int depth) {
        if (key.second == 0) return -1;
        int index = key.second - 1;
        for (; index >= std::max(0, (int) key.second - depth); --index) {
            if (page_cache_.Get(std::make_pair(key.first, (uint64_t) index), false) == nullptr) return index;
        }
        return index - 1;
    }

    int FindClosestHoleAfter(PageCache::KeyType key, int depth) {
        int index = key.second + 1;
        for (; index <= key.second + depth; ++index) {
            if (page_cache_.Get(std::make_pair(key.first, (uint64_t) index), false) == nullptr) return index;
        }
        return index + 1;
    }

    void SubmitRead(uint64_t ino, uint64_t start, uint64_t size, int lookahead_index) {
        for (uint64_t index = start; index < start + size; ++index) {
            page_cache_.Put(std::make_pair(ino, index), index == lookahead_index);
        }
    }

    bool Simulate(uint64_t ino, uint64_t start, uint64_t size) {
        auto stat = Statistics::GetInstance();
        bool cache_hit = true;
        for (uint64_t index = start; index < start + size; ++index) {
            uint64_t current_size = start + size - index;
            PageCache::KeyType key = std::make_pair(ino, index);
            auto iter = readahead_structs_.find(ino);
            if (iter == readahead_structs_.end()) {
                auto ret = readahead_structs_.insert(std::make_pair(ino, Readahead(this)));
                iter = ret.first;
            }
            PageCacheItem* cache_item = page_cache_.Get(key, true);
            if (cache_item == nullptr) {
                iter->second.Update(key, current_size, false);
                cache_hit = false;
            } else if (cache_item->readahead_mark) {
                iter->second.Update(key, current_size, true);
                cache_item->readahead_mark = false;
            }
            iter->second.prev_index_ = index;
        }
        return cache_hit;
    }
};
