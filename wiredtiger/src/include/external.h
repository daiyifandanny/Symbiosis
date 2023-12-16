#include <stdint.h>
#include <threads.h>

#if defined(__cplusplus)
extern "C" {
#endif

extern thread_local uint8_t app_cache_hit;
extern thread_local uint64_t app_cache_id;
extern thread_local uint64_t app_cache_size;
extern uint64_t kernel_cache_time;
extern uint64_t kernel_cache_start;
extern uint64_t kernel_cache_size;


#if defined(__cplusplus)
}
#endif
