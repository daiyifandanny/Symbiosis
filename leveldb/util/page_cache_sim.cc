#include "page_cache_sim.h"
#include "stats.h"


void DeletePCItem(const Slice& key, void* value) {
    auto item = reinterpret_cast<PageCacheItem*>(value);
    delete item;
}

void Readahead::Update(PageCache::KeyType key, int size, bool mark_hit) {
    auto stat = Statistics::GetInstance();
    int seq_length = -1;
    uint64_t target = key.second;
    
    if (target == 0) {
        start_index_ = target;
        current_readahead_ = InitRaValue(size);
        lookahead_index_ = start_index_ + (current_readahead_ > size ? size : 0);
    } else if (start_index_ != -1 && (target == start_index_ + current_readahead_ || target == lookahead_index_)) {
        start_index_ += current_readahead_;
        current_readahead_ = NextRaValue();
        lookahead_index_ = start_index_;
    } else if (mark_hit) {
        int start = page_cache_->FindClosestHoleAfter(key, max_readahead_);
        if (start - target == max_readahead_ + 1) start -= 1;
        if (start - target > max_readahead_) {
            return;
        }

        start_index_ = start;
        current_readahead_ = start - target;
        current_readahead_ += size;
        current_readahead_ = NextRaValue();
        lookahead_index_ = start_index_;
    } else if (size > max_readahead_) {
        start_index_ = target;
        current_readahead_ = max_readahead_;
        lookahead_index_ = start_index_;
    } else if (prev_index_ != -1 && target - prev_index_ <= 1 && target >= prev_index_) {
        start_index_ = target;
        current_readahead_ = InitRaValue(size);
        lookahead_index_ = start_index_ + (current_readahead_ > size ? size : 0);
    } else if ((seq_length = target - page_cache_->FindClosestHoleBefore(key, max_readahead_) - 1) > size) {
        if (seq_length >= target) seq_length *= 2;
        start_index_ = target;
        AssignRaValue(seq_length + size);
        lookahead_index_ = start_index_ + current_readahead_ - 1;
    } else {
        page_cache_->SubmitRead(key.first, target, size, -1);
        return;
    }
    if (target == start_index_ && lookahead_index_ == start_index_) {
        int next_readahead = NextRaValue();
        if (current_readahead_ + next_readahead <= max_readahead_) {
            lookahead_index_ += current_readahead_;
            current_readahead_ += next_readahead;
        } else {
            current_readahead_ = max_readahead_;
            lookahead_index_ += max_readahead_ / 2;
        }
    }
    page_cache_->SubmitRead(key.first, start_index_, current_readahead_, lookahead_index_);
    return;
}