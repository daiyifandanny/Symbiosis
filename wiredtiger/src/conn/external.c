#include "external.h"

thread_local uint8_t app_cache_hit;
thread_local uint64_t app_cache_id;
thread_local uint64_t app_cache_size;
uint64_t kernel_cache_time;
uint64_t kernel_cache_start;
uint64_t kernel_cache_size;
