#ifdef __INTELLISENSE__
#pragma diag_suppress 393
#pragma diag_suppress 757
#pragma diag_suppress 65
#pragma diag_suppress 40
#pragma diag_suppress 151
#pragma diag_suppress 100
#pragma diag_suppress 20
#pragma diag_suppress 32
#pragma diag_suppress 1696
#pragma diag_suppress 18
#endif

#include <uapi/linux/ptrace.h>
#include <linux/blkdev.h>
#include <linux/mm_types.h>
#include <linux/mm.h>
#include <linux/types.h>
#include <linux/memcontrol.h>

struct pcache_miss_stat {
    u64 time;
    u32 arg;
    u32 page_count;
    u32 evicted_count;
    u32 sync_count;
    u32 async_count;
    u32 sync_num;
    u32 async_num;
};

struct pcache_key {
    u64 ino;
    u64 offset;
};

struct pid_size {
    u64 size;
    u32 pid;
};

BPF_HASH(page_cache, struct pcache_key, u32, 10485760);
BPF_HASH(pcache_thrashing_count, u32, u32);
// BPF_QUEUE(page_cache_trace, u64, 10485760);
// BPF_HASH(page_cache_evictions, unsigned long, u32, 10485760);



BPF_HASH(fcache_start_ts, u32, u64);
BPF_HASH(fcache_fs_hit_time, u32, u64);
BPF_HASH(fcache_fs_hit_num, u32, u32);
BPF_HASH(fcache_fs_start, u32, u64);
BPF_HASH(fcache_fs_time, u32, u64);
BPF_HASH(fcache_pcache_miss_time, u32, u64);
BPF_HASH(fcache_pcache_miss_num, u32, u32);
BPF_HASH(fcache_pcache_miss_flag, u32, u32);
BPF_HASH(fcache_pcache_miss_page_count, u32, u32);
// BPF_QUEUE(fcache_pcache_miss_sample, struct pcache_miss_stat, 1048576);
BPF_HASH(fcache_pcache_evicted_flag, u32, u32);
BPF_HASH(fcache_pcache_evicted_page_count, u32, u32);
BPF_HASH(fcache_blk_flag, u32, u32);
BPF_HASH(fcache_blk_page_count, u32, u32);
BPF_HASH(fcache_sync_flag, u32, u32);
BPF_HASH(fcache_sync_count, u32, u32);
BPF_HASH(fcache_sync_start, u32, u32);
BPF_HASH(fcache_async_flag, u32, u32);
BPF_HASH(fcache_async_count, u32, u32);
BPF_HASH(fcache_async_start, u32, u32);
BPF_HASH(fcache_sync_num, u32, u32);
BPF_HASH(fcache_async_num, u32, u32);
BPF_HASH(fcache_hit_num, u32, u32);
BPF_HASH(fcache_hit_time, u32, u64);
BPF_HASH(fcache_miss_num, u32, u32);
BPF_HASH(fcache_miss_time, u32, u64);
BPF_HASH(fcache_activation_num, u32, u32);


int fcache_start(struct pt_regs *ctx) {
    u32 pid, zero32;
    u64 ts, zero64, *init;
    
    zero32 = 0;
    zero64 = 0;
    pid = bpf_get_current_pid_tgid();
    ts = bpf_ktime_get_ns();
    fcache_start_ts.update(&pid, &ts);
    fcache_fs_time.update(&pid, &zero64);
    fcache_pcache_miss_flag.update(&pid, &zero32);
    fcache_pcache_evicted_flag.update(&pid, &zero32);
    fcache_sync_flag.update(&pid, &zero32);
    fcache_async_flag.update(&pid, &zero32);

    init = fcache_fs_hit_time.lookup(&pid);
    if (init == 0) {
        fcache_fs_hit_time.update(&pid, &zero64);
        fcache_fs_hit_num.update(&pid, &zero32);
        fcache_pcache_miss_time.update(&pid, &zero64);
        fcache_pcache_miss_num.update(&pid, &zero32);
        fcache_pcache_miss_page_count.update(&pid, &zero32);
        fcache_pcache_evicted_page_count.update(&pid, &zero32);
        fcache_sync_count.update(&pid, &zero32);
        fcache_async_count.update(&pid, &zero32);
        fcache_sync_num.update(&pid, &zero32);
        fcache_async_num.update(&pid, &zero32);
        pcache_thrashing_count.update(&zero32, &zero32);
        fcache_hit_num.update(&pid, &zero32);
        fcache_miss_num.update(&pid, &zero32);
        fcache_hit_time.update(&pid, &zero64);
        fcache_miss_time.update(&pid, &zero64);
        fcache_activation_num.update(&pid, &zero32);
    }
    // bpf_trace_printk("fcache_start\n");
    return 0;
}

int fcache_end(struct pt_regs *ctx) {
    u32 pid, *pcache_miss_flag, *total_num, *total_page_count, *pcache_evicted_flag, *total_evicted_count;
    u32 *total_blk_count, *blk_flag, *pcache_value, *sync_flag, *sync_count, *async_flag, *async_count;
    u32 *sync_num, *async_num;
    u64 delta, *start_ts, *total_time, *u64ptr;
    struct pcache_miss_stat stat = {};
    struct pcache_key pkey = {};
    
    pid = bpf_get_current_pid_tgid();
    start_ts = fcache_start_ts.lookup(&pid);
    pcache_miss_flag = fcache_pcache_miss_flag.lookup(&pid);
    pcache_evicted_flag = fcache_pcache_evicted_flag.lookup(&pid);
    sync_flag = fcache_sync_flag.lookup(&pid);
    async_flag = fcache_async_flag.lookup(&pid);
    
    if (start_ts != 0 && pcache_miss_flag != 0 && pcache_evicted_flag != 0 && sync_flag != 0 && async_flag != 0) {
        delta = bpf_ktime_get_ns() - *start_ts;

        bpf_usdt_readarg(1, ctx, &pkey.ino);
        bpf_usdt_readarg(2, ctx, &pkey.offset);

        if (pkey.ino == 1) {
            total_time = fcache_hit_time.lookup(&pid);
            total_num = fcache_hit_num.lookup(&pid);
            if (total_time != 0 && total_num != 0) {
                *total_time += delta / 1000;
                *total_num += 1;
            }
        } else {
            if (*sync_flag == 0) {
                total_time = fcache_miss_time.lookup(&pid);
                total_num = fcache_miss_num.lookup(&pid);
                if (total_time != 0 && total_num != 0) {
                    *total_time += delta / 1000;
                    *total_num += 1;
                }

                u64ptr = fcache_fs_time.lookup(&pid);
                if (u64ptr != 0 && *u64ptr != 0) {
                    total_time = fcache_fs_hit_time.lookup(&pid);
                    total_num = fcache_fs_hit_num.lookup(&pid);
                    if (total_time != 0 && total_num != 0) {
                        *total_time += *u64ptr;
                        *total_num += 1;
                    }
                }
            } else {
                total_time = fcache_pcache_miss_time.lookup(&pid);
                total_num = fcache_pcache_miss_num.lookup(&pid);
                if (total_time != 0 && total_num != 0) {
                    *total_time += delta / 1000;
                    *total_num += 1;
                }                
            }
        }

        total_page_count = fcache_pcache_miss_page_count.lookup(&pid);
        if (total_page_count != 0) {
            *total_page_count += *pcache_miss_flag;
        }

        stat.arg = pkey.offset;
        stat.page_count = *pcache_miss_flag;
        stat.evicted_count = *pcache_evicted_flag;
        stat.sync_count = *sync_flag % 1000000;
        stat.sync_num = *sync_flag / 1000000;
        stat.async_count = *async_flag % 1000000;
        stat.async_num = *async_flag / 1000000;
        stat.time = delta / 1000;
        // fcache_pcache_miss_sample.push(&stat, BPF_EXIST);
        total_evicted_count = fcache_pcache_evicted_page_count.lookup(&pid);
        if (total_evicted_count != 0) {
            *total_evicted_count += stat.evicted_count;
        }

        sync_count = fcache_sync_count.lookup(&pid);
        if (sync_count != 0) {
            *sync_count += stat.sync_count;
        }

        async_count = fcache_async_count.lookup(&pid);
        if (async_count != 0) {
            *async_count += stat.async_count;
        }

        sync_num = fcache_sync_num.lookup(&pid);
        if (sync_num != 0 && stat.sync_num != 0) {
            *sync_num += stat.sync_num;
        }

        async_num = fcache_async_num.lookup(&pid);
        if (async_num != 0 && stat.async_num != 0) {
            *async_num += stat.async_num;
        }
        // bpf_trace_printk("fcache page %u sync %u async %u\n", stat.page_count, stat.sync_count, stat.async_count);
        
        fcache_start_ts.delete(&pid);
        fcache_fs_time.delete(&pid);
        fcache_pcache_miss_flag.delete(&pid);
        fcache_pcache_evicted_flag.delete(&pid);
        fcache_sync_flag.delete(&pid);
        fcache_async_flag.delete(&pid);

        // bpf_trace_printk("fcache_end on target %lu\n", pkey.offset);
    }

    return 0;
}

BPF_HASH(bcache_start_ts, u32, u64);
BPF_HASH(bcache_fs_hit_time, u32, u64);
BPF_HASH(bcache_fs_hit_num, u32, u32);
BPF_HASH(bcache_fs_start, u32, u64);
BPF_HASH(bcache_fs_time, u32, u64);
BPF_HASH(bcache_pcache_miss_time, u32, u64);
BPF_HASH(bcache_pcache_miss_num, u32, u32);
BPF_HASH(bcache_pcache_miss_flag, u32, u32);
BPF_HASH(bcache_pcache_miss_page_count, u32, u32);
// BPF_QUEUE(bcache_pcache_miss_sample, struct pcache_miss_stat, 1048576);
BPF_HASH(bcache_pcache_evicted_flag, u32, u32);
BPF_HASH(bcache_pcache_evicted_page_count, u32, u32);
BPF_HASH(bcache_blk_flag, u32, u32);
BPF_HASH(bcache_blk_page_count, u32, u32);
BPF_HASH(bcache_sync_flag, u32, u32);
BPF_HASH(bcache_sync_count, u32, u32);
BPF_HASH(bcache_sync_start, u32, u32);
BPF_HASH(bcache_async_flag, u32, u32);
BPF_HASH(bcache_async_count, u32, u32);
BPF_HASH(bcache_async_start, u32, u32);
BPF_HASH(bcache_sync_num, u32, u32);
BPF_HASH(bcache_async_num, u32, u32);
BPF_HASH(bcache_hit_num, u32, u32);
BPF_HASH(bcache_hit_time, u32, u64);
BPF_HASH(bcache_miss_num, u32, u32);
BPF_HASH(bcache_miss_time, u32, u64);


int bcache_start(struct pt_regs *ctx) {
    u32 pid, zero32;
    u64 ts, zero64, *init;
    
    zero32 = 0;
    zero64 = 0;
    pid = bpf_get_current_pid_tgid();
    ts = bpf_ktime_get_ns();
    bcache_start_ts.update(&pid, &ts);
    bcache_fs_time.update(&pid, &zero64);
    bcache_pcache_miss_flag.update(&pid, &zero32);
    bcache_pcache_evicted_flag.update(&pid, &zero32);
    bcache_sync_flag.update(&pid, &zero32);
    bcache_async_flag.update(&pid, &zero32);

    init = bcache_fs_hit_time.lookup(&pid);
    if (init == 0) {
        bcache_fs_hit_time.update(&pid, &zero64);
        bcache_fs_hit_num.update(&pid, &zero32);
        bcache_pcache_miss_time.update(&pid, &zero64);
        bcache_pcache_miss_num.update(&pid, &zero32);
        bcache_pcache_miss_page_count.update(&pid, &zero32);
        bcache_pcache_evicted_page_count.update(&pid, &zero32);
        bcache_sync_count.update(&pid, &zero32);
        bcache_async_count.update(&pid, &zero32);
        bcache_sync_num.update(&pid, &zero32);
        bcache_async_num.update(&pid, &zero32);
        pcache_thrashing_count.update(&zero32, &zero32);
        bcache_hit_num.update(&pid, &zero32);
        bcache_miss_num.update(&pid, &zero32);
        bcache_hit_time.update(&pid, &zero64);
        bcache_miss_time.update(&pid, &zero64);
    }
    
    return 0;
}

int bcache_end(struct pt_regs *ctx) {
    u32 pid, *pcache_miss_flag, *total_num, *total_page_count, *pcache_evicted_flag, *total_evicted_count;
    u32 *total_blk_count, *blk_flag, *pcache_value, *sync_flag, *sync_count, *async_flag, *async_count;
    u32 *sync_num, *async_num;
    u64 delta, *start_ts, *total_time, *u64ptr;
    struct pcache_miss_stat stat = {};
    struct pcache_key pkey = {};
    
    pid = bpf_get_current_pid_tgid();
    start_ts = bcache_start_ts.lookup(&pid);
    pcache_miss_flag = bcache_pcache_miss_flag.lookup(&pid);
    pcache_evicted_flag = bcache_pcache_evicted_flag.lookup(&pid);
    sync_flag = bcache_sync_flag.lookup(&pid);
    async_flag = bcache_async_flag.lookup(&pid);
    
    if (start_ts != 0 && pcache_miss_flag != 0 && pcache_evicted_flag != 0 && sync_flag != 0 && async_flag != 0) {
        delta = bpf_ktime_get_ns() - *start_ts;

        bpf_usdt_readarg(1, ctx, &pkey.ino);
        bpf_usdt_readarg(2, ctx, &pkey.offset);

        if (pkey.ino == 1) {
            total_time = bcache_hit_time.lookup(&pid);
            total_num = bcache_hit_num.lookup(&pid);
            if (total_time != 0 && total_num != 0) {
                *total_time += delta / 1000;
                *total_num += 1;
            }
        } else {
            if (*sync_flag == 0) {
                total_time = bcache_miss_time.lookup(&pid);
                total_num = bcache_miss_num.lookup(&pid);
                if (total_time != 0 && total_num != 0) {
                    *total_time += delta / 1000;
                    *total_num += 1;
                }

                u64ptr = bcache_fs_time.lookup(&pid);
                if (u64ptr != 0 && *u64ptr != 0) {
                    total_time = bcache_fs_hit_time.lookup(&pid);
                    total_num = bcache_fs_hit_num.lookup(&pid);
                    if (total_time != 0 && total_num != 0) {
                        *total_time += *u64ptr;
                        *total_num += 1;
                    }
                }
            } else {
                total_time = bcache_pcache_miss_time.lookup(&pid);
                total_num = bcache_pcache_miss_num.lookup(&pid);
                if (total_time != 0 && total_num != 0) {
                    *total_time += delta / 1000;
                    *total_num += 1;
                }                
            }
        }

        total_page_count = bcache_pcache_miss_page_count.lookup(&pid);
        if (total_page_count != 0) {
            *total_page_count += *pcache_miss_flag;
        }

        stat.arg = pkey.offset;
        stat.page_count = *pcache_miss_flag;
        stat.evicted_count = *pcache_evicted_flag;
        stat.sync_count = *sync_flag % 1000000;
        stat.sync_num = *sync_flag / 1000000;
        stat.async_count = *async_flag % 1000000;
        stat.async_num = *async_flag / 1000000;
        stat.time = delta / 1000;
        // bcache_pcache_miss_sample.push(&stat, BPF_EXIST);
        total_evicted_count = bcache_pcache_evicted_page_count.lookup(&pid);
        if (total_evicted_count != 0) {
            *total_evicted_count += stat.evicted_count;
        }

        sync_count = bcache_sync_count.lookup(&pid);
        if (sync_count != 0) {
            *sync_count += stat.sync_count;
        }

        async_count = bcache_async_count.lookup(&pid);
        if (async_count != 0) {
            *async_count += stat.async_count;
        }

        sync_num = bcache_sync_num.lookup(&pid);
        if (sync_num != 0) {
            *sync_num += stat.sync_num;
        }

        async_num = bcache_async_num.lookup(&pid);
        if (async_num != 0) {
            *async_num += stat.async_num;
        }
        
        bcache_start_ts.delete(&pid);
        bcache_fs_time.delete(&pid);
        bcache_pcache_miss_flag.delete(&pid);
        bcache_pcache_evicted_flag.delete(&pid);
        bcache_sync_flag.delete(&pid);
        bcache_async_flag.delete(&pid);
    }
    return 0;
}

BPF_HASH(search1_start_ts, u32, u64);
BPF_HASH(search1_fs_hit_time, u32, u64);
BPF_HASH(search1_fs_hit_num, u32, u32);
BPF_HASH(search1_fs_start, u32, u64);
BPF_HASH(search1_fs_time, u32, u64);
BPF_HASH(search1_pcache_miss_time, u32, u64);
BPF_HASH(search1_pcache_miss_num, u32, u32);
BPF_HASH(search1_pcache_miss_flag, u32, u32);
BPF_HASH(search1_pcache_miss_page_count, u32, u32);
// BPF_QUEUE(search1_pcache_miss_sample, struct pcache_miss_stat, 1048576);
BPF_HASH(search1_pcache_evicted_flag, u32, u32);
BPF_HASH(search1_pcache_evicted_page_count, u32, u32);
BPF_HASH(search1_blk_flag, u32, u32);
BPF_HASH(search1_blk_page_count, u32, u32);
BPF_HASH(search1_sync_flag, u32, u32);
BPF_HASH(search1_sync_count, u32, u32);
BPF_HASH(search1_sync_start, u32, u32);
BPF_HASH(search1_async_flag, u32, u32);
BPF_HASH(search1_async_count, u32, u32);
BPF_HASH(search1_async_start, u32, u32);
BPF_HASH(search1_sync_num, u32, u32);
BPF_HASH(search1_async_num, u32, u32);
BPF_HASH(search1_hit_num, u32, u32);
BPF_HASH(search1_hit_time, u32, u64);
BPF_HASH(search1_miss_num, u32, u32);
BPF_HASH(search1_miss_time, u32, u64);


int search1_start(struct pt_regs *ctx) {
    u32 pid, zero32;
    u64 ts, zero64, *init;
    
    zero32 = 0;
    zero64 = 0;
    pid = bpf_get_current_pid_tgid();
    ts = bpf_ktime_get_ns();
    search1_start_ts.update(&pid, &ts);
    search1_fs_time.update(&pid, &zero64);
    search1_pcache_miss_flag.update(&pid, &zero32);
    search1_pcache_evicted_flag.update(&pid, &zero32);
    search1_sync_flag.update(&pid, &zero32);
    search1_async_flag.update(&pid, &zero32);

    init = search1_fs_hit_time.lookup(&pid);
    if (init == 0) {
        search1_fs_hit_time.update(&pid, &zero64);
        search1_fs_hit_num.update(&pid, &zero32);
        search1_pcache_miss_time.update(&pid, &zero64);
        search1_pcache_miss_num.update(&pid, &zero32);
        search1_pcache_miss_page_count.update(&pid, &zero32);
        search1_pcache_evicted_page_count.update(&pid, &zero32);
        search1_sync_count.update(&pid, &zero32);
        search1_async_count.update(&pid, &zero32);
        search1_sync_num.update(&pid, &zero32);
        search1_async_num.update(&pid, &zero32);
        pcache_thrashing_count.update(&zero32, &zero32);
        search1_hit_num.update(&pid, &zero32);
        search1_miss_num.update(&pid, &zero32);
        search1_hit_time.update(&pid, &zero64);
        search1_miss_time.update(&pid, &zero64);
    }

    return 0;
}

int search1_end(struct pt_regs *ctx) {
    u32 pid, *pcache_miss_flag, *total_num, *total_page_count, *pcache_evicted_flag, *total_evicted_count;
    u32 *total_blk_count, *blk_flag, *pcache_value, *sync_flag, *sync_count, *async_flag, *async_count;
    u32 *sync_num, *async_num;
    u64 delta, *start_ts, *total_time, *u64ptr;
    struct pcache_miss_stat stat = {};
    struct pcache_key pkey = {};
    
    pid = bpf_get_current_pid_tgid();
    start_ts = search1_start_ts.lookup(&pid);
    pcache_miss_flag = search1_pcache_miss_flag.lookup(&pid);
    pcache_evicted_flag = search1_pcache_evicted_flag.lookup(&pid);
    sync_flag = search1_sync_flag.lookup(&pid);
    async_flag = search1_async_flag.lookup(&pid);
    
    if (start_ts != 0 && pcache_miss_flag != 0 && pcache_evicted_flag != 0 && sync_flag != 0 && async_flag != 0) {
        delta = bpf_ktime_get_ns() - *start_ts;

        bpf_usdt_readarg(1, ctx, &pkey.ino);
        bpf_usdt_readarg(2, ctx, &pkey.offset);

        if (pkey.ino == 1) {
            total_time = search1_hit_time.lookup(&pid);
            total_num = search1_hit_num.lookup(&pid);
            if (total_time != 0 && total_num != 0) {
                *total_time += delta / 1000;
                *total_num += 1;
            }
        } else {
            if (*sync_flag == 0) {
                total_time = search1_miss_time.lookup(&pid);
                total_num = search1_miss_num.lookup(&pid);
                if (total_time != 0 && total_num != 0) {
                    *total_time += delta / 1000;
                    *total_num += 1;
                }

                u64ptr = search1_fs_time.lookup(&pid);
                if (u64ptr != 0 && *u64ptr != 0) {
                    total_time = search1_fs_hit_time.lookup(&pid);
                    total_num = search1_fs_hit_num.lookup(&pid);
                    if (total_time != 0 && total_num != 0) {
                        *total_time += *u64ptr;
                        *total_num += 1;
                    }
                }
            } else {
                total_time = search1_pcache_miss_time.lookup(&pid);
                total_num = search1_pcache_miss_num.lookup(&pid);
                if (total_time != 0 && total_num != 0) {
                    *total_time += delta / 1000;
                    *total_num += 1;
                }                
            }
        }

        total_page_count = search1_pcache_miss_page_count.lookup(&pid);
        if (total_page_count != 0) {
            *total_page_count += *pcache_miss_flag;
        }

        stat.arg = pkey.offset;
        stat.page_count = *pcache_miss_flag;
        stat.evicted_count = *pcache_evicted_flag;
        stat.sync_count = *sync_flag % 1000000;
        stat.sync_num = *sync_flag / 1000000;
        stat.async_count = *async_flag % 1000000;
        stat.async_num = *async_flag / 1000000;
        stat.time = delta / 1000;
        // search1_pcache_miss_sample.push(&stat, BPF_EXIST);
        total_evicted_count = search1_pcache_evicted_page_count.lookup(&pid);
        if (total_evicted_count != 0) {
            *total_evicted_count += stat.evicted_count;
        }

        sync_count = search1_sync_count.lookup(&pid);
        if (sync_count != 0) {
            *sync_count += stat.sync_count;
        }

        async_count = search1_async_count.lookup(&pid);
        if (async_count != 0) {
            *async_count += stat.async_count;
        }

        sync_num = search1_sync_num.lookup(&pid);
        if (sync_num != 0) {
            *sync_num += stat.sync_num;
        }

        async_num = search1_async_num.lookup(&pid);
        if (async_num != 0) {
            *async_num += stat.async_num;
        }
        
        search1_start_ts.delete(&pid);
        search1_fs_time.delete(&pid);
        search1_pcache_miss_flag.delete(&pid);
        search1_pcache_evicted_flag.delete(&pid);
        search1_sync_flag.delete(&pid);
        search1_async_flag.delete(&pid);
    }

    return 0;
}






int pcache_detect_miss(struct pt_regs *ctx, struct page *page) {
    u32 pid, *miss_flag, *pcache_value, zero32, total_flag;
    struct pcache_key pkey = {};
    
    zero32 = 0;
    total_flag = 0;
    pid = bpf_get_current_pid_tgid();

    if (page->mapping->host != 0) {
        pkey.ino = page->mapping->host->i_ino;
        if (pkey.ino != 0) {
            miss_flag = fcache_pcache_miss_flag.lookup(&pid);
            if (miss_flag != 0) {
                *miss_flag += 1;
                total_flag += *miss_flag;
            }

            miss_flag = bcache_pcache_miss_flag.lookup(&pid);
            if (miss_flag != 0) {
                *miss_flag += 1;
                total_flag += *miss_flag;
            }

            miss_flag = search1_pcache_miss_flag.lookup(&pid);
            if (miss_flag != 0) {
                *miss_flag += 1;
                total_flag += *miss_flag;
            }

            if (total_flag != 0) {
                pkey.offset = page->index;
                pcache_value = page_cache.lookup(&pkey);
                if (pcache_value == 0) {
                    page_cache.update(&pkey, &zero32);
                    // bpf_trace_printk("debug: pcache entry inserted: %lu, %lu\n", pkey.ino, pkey.offset);
                } else {
                    bpf_trace_printk("debug: pcache entry exists: %lu, %lu\n", pkey.ino, pkey.offset);
                }
                // page_cache_trace.push(&(pkey.offset), BPF_EXIST);
            }
        }
    }

    return 0;
}

int pcache_detect_eviction(struct pt_regs *ctx, struct page *page) {
    u32 pid, *evicted_flag, *pcache_value, *total_thrashing_count, zero32, total_flag, *memcg_count;
    unsigned long memcg_data;
    struct pcache_key pkey = {};
    
    zero32 = 0;
    total_flag = 0;
    pid = bpf_get_current_pid_tgid();

    if (page->mapping->host != 0) {
        pkey.ino = page->mapping->host->i_ino;
        if (pkey.ino != 0) {
            evicted_flag = fcache_pcache_evicted_flag.lookup(&pid);
            if (evicted_flag != 0) {
                *evicted_flag += 1;
                total_flag += *evicted_flag;
            }

            evicted_flag = bcache_pcache_evicted_flag.lookup(&pid);
            if (evicted_flag != 0) {
                *evicted_flag += 1;
                total_flag += *evicted_flag;
            }

            evicted_flag = search1_pcache_evicted_flag.lookup(&pid);
            if (evicted_flag != 0) {
                *evicted_flag += 1;
                total_flag += *evicted_flag;
            }

            if (1) {
                pkey.offset = page->index;
                pcache_value = page_cache.lookup(&pkey);
                if (pcache_value == 0) {
                    // bpf_trace_printk("debug: pcache entry not found for deletion: %lu, %lu\n", pkey.ino, pkey.offset);
                } else {
                    page_cache.delete(&pkey);
                    // bpf_trace_printk("debug: pcache entry deleted: %lu, %lu, %u\n", pkey.ino, pkey.offset, *pcache_value);
                    if (*pcache_value == 0) {
                        total_thrashing_count = pcache_thrashing_count.lookup(&zero32);
                        if (total_thrashing_count != 0) {
                            *total_thrashing_count += 1;
                        }
                        // bpf_trace_printk("RA THRASHING: %lu, %lu\n", pkey.ino, pkey.offset);
                    }
                }
            }
        }
        // bpf_trace_printk("%lu\n", page->memcg_data);
        // memcg_data = page->memcg_data;
        // memcg_count = page_cache_evictions.lookup(&memcg_data);
        // if (memcg_count == 0) {
        //     page_cache_evictions.update(&memcg_data, &zero32);
        // } else {
        //     *memcg_count += 1;
        // }
    }

    return 0;
}

int pcache_detect_sync(struct pt_regs *ctx) {
    u32 pid, *sync_flag, zero32 = 0;

    pid = bpf_get_current_pid_tgid();

    sync_flag = fcache_sync_flag.lookup(&pid);
    if (sync_flag != 0) {
        fcache_sync_start.update(&pid, &zero32);
    }

    sync_flag = bcache_sync_flag.lookup(&pid);
    if (sync_flag != 0) {
        bcache_sync_start.update(&pid, &zero32);
    }

    sync_flag = search1_sync_flag.lookup(&pid);
    if (sync_flag != 0) {
        search1_sync_start.update(&pid, &zero32);
    }

    return 0;
}

int pcache_detect_sync_ret(struct pt_regs *ctx) {
    u32 pid;

    pid = bpf_get_current_pid_tgid();
    fcache_sync_start.delete(&pid);

    pid = bpf_get_current_pid_tgid();
    bcache_sync_start.delete(&pid);

    pid = bpf_get_current_pid_tgid();
    search1_sync_start.delete(&pid);

    return 0;
}

int pcache_detect_async(struct pt_regs *ctx) {
    u32 pid, *async_flag, zero32 = 0;

    pid = bpf_get_current_pid_tgid();

    async_flag = fcache_async_flag.lookup(&pid);
    if (async_flag != 0) {
        fcache_async_start.update(&pid, &zero32);
    }

    async_flag = bcache_async_flag.lookup(&pid);
    if (async_flag != 0) {
        bcache_async_start.update(&pid, &zero32);
    }

    async_flag = search1_async_flag.lookup(&pid);
    if (async_flag != 0) {
        search1_async_start.update(&pid, &zero32);
    }

    return 0;
}

int pcache_detect_async_ret(struct pt_regs *ctx) {
    u32 pid;

    pid = bpf_get_current_pid_tgid();
    fcache_async_start.delete(&pid);

    pid = bpf_get_current_pid_tgid();
    bcache_async_start.delete(&pid);

    pid = bpf_get_current_pid_tgid();
    search1_async_start.delete(&pid);

    return 0;
}

int detect_blk(struct pt_regs *ctx, struct request* req) {
    u32 pid, *sync_flag, *async_flag, *sync_start, *async_start;

    pid = bpf_get_current_pid_tgid();

    sync_flag = fcache_sync_flag.lookup(&pid);
    if (sync_flag != 0) {
        sync_start = fcache_sync_start.lookup(&pid);
        if (sync_start != 0) {
            *sync_flag += req->__data_len / 4096;
            *sync_flag += 1000000;
        }
    }

    async_flag = fcache_async_flag.lookup(&pid);
    if (async_flag != 0) {
        async_start = fcache_async_start.lookup(&pid);
        if (async_start != 0) {
            *async_flag += req->__data_len / 4096;
            *async_flag += 1000000;
        }
    }

    sync_flag = bcache_sync_flag.lookup(&pid);
    if (sync_flag != 0) {
        sync_start = bcache_sync_start.lookup(&pid);
        if (sync_start != 0) {
            *sync_flag += req->__data_len / 4096;
            *sync_flag += 1000000;
        }        
    }

    async_flag = bcache_async_flag.lookup(&pid);
    if (async_flag != 0) {
        async_start = bcache_async_start.lookup(&pid);
        if (async_start != 0) {
            *async_flag += req->__data_len / 4096;
            *async_flag += 1000000;
        }
    }

    sync_flag = search1_sync_flag.lookup(&pid);
    if (sync_flag != 0) {
        sync_start = search1_sync_start.lookup(&pid);
        if (sync_start != 0) {
            *sync_flag += req->__data_len / 4096;
            *sync_flag += 1000000;
        }        
    }

    async_flag = search1_async_flag.lookup(&pid);
    if (async_flag != 0) {
        async_start = search1_async_start.lookup(&pid);
        if (async_start != 0) {
            *async_flag += req->__data_len / 4096;
            *async_flag += 1000000;
        }
    }



    // blk_flag = fcache_blk_flag.lookup(&pid);
    // if (blk_flag != 0) {
    //     ps.pid = pid;
    //     ps.size = req->__data_len;
    //     blk_request.update(&req, &ps);
    //     // *blk_flag += req->__data_len;
    // }
    // else if ((req->cmd_flags & REQ_OP_MASK) == REQ_OP_READ) {
    //     bpf_trace_printk("uncaught read size = %u\n", req->__data_len);
    // }

    // blk_flag = bcache_blk_flag.lookup(&pid);
    // if (blk_flag != 0) {
    //     *blk_flag += req->__data_len;
    // }

    // blk_flag = search1_blk_flag.lookup(&pid);
    // if (blk_flag != 0) {
    //     *blk_flag += req->__data_len;
    // }

    // blk_flag = search2_blk_flag.lookup(&pid);
    // if (blk_flag != 0) {
    //     *blk_flag += req->__data_len;
    // }

    return 0;
}

// int detect_blk_return(struct pt_regs *ctx, struct request* req) {
//     u32 *blk_flag;
//     struct pid_size* ps;

//     ps = blk_request.lookup(&req);
//     if (ps != 0) {
//         blk_flag = fcache_blk_flag.lookup(&ps->pid);
//         if (blk_flag != 0) {
//             *blk_flag += ps->size;
//             // bpf_trace_printk("blk_return with size %lu\n", req->__data_len);
//         }
//         blk_request.delete(&req);
//     }

//     return 0;
// }


int detect_activation(struct pt_regs *ctx) {
    u32 zero32, pid, *count;
    u64 *ts;
    
    zero32 = 0;
    pid = bpf_get_current_pid_tgid();
    ts = fcache_start_ts.lookup(&pid);
    if (ts != 0) {
        count = fcache_activation_num.lookup(&pid);
        if (count != 0) {
            *count += 1;
        }
    }

    return 0;
}


int pcache_detect_access1(struct pt_regs *ctx) {
    u32 *pcache_value;
    struct pcache_key pkey = {};

    bpf_usdt_readarg(1, ctx, &pkey.ino);
    bpf_usdt_readarg(2, ctx, &pkey.offset);
    bpf_trace_printk("debug: pcache entry access called: %lu, %lu\n", pkey.ino, pkey.offset);
    if (pkey.ino != 0) {
        pcache_value = page_cache.lookup(&pkey);
        if (pcache_value == 0) {
            // bpf_trace_printk("debug: pcache entry not found for access1: %lu, %lu\n", pkey.ino, pkey.offset);
        } else {
            *pcache_value += 1;
            // bpf_trace_printk("debug: pcache entry accessed: %lu, %lu\n", pkey.ino, pkey.offset);
        }            
    }

    return 0;
}

int pcache_detect_access2(struct pt_regs *ctx) {
    u32 *pcache_value;
    struct pcache_key pkey = {};

    bpf_usdt_readarg(1, ctx, &pkey.ino);
    bpf_usdt_readarg(2, ctx, &pkey.offset);
    if (pkey.ino != 0) {
        pcache_value = page_cache.lookup(&pkey);
        if (pcache_value == 0) {
            // bpf_trace_printk("debug: pcache entry not found for access2: %lu, %lu\n", pkey.ino, pkey.offset);
        } else {
            *pcache_value += 1;
            // bpf_trace_printk("debug: pcache entry accessed: %lu, %lu\n", pkey.ino, pkey.offset);
        }
    }

    return 0;
}


BPF_HASH(memcontrol_time, u32, u64);
BPF_HASH(memcontrol_num, u32, u32);
BPF_HASH(memcontrol_start, u32, u64);

int detect_fs(struct pt_regs *ctx) {
    u32 pid, zero32, *u32ptr, flag;
    u64 *u64ptr, zero64, time;

    flag = 0;
    zero32 = 0;
    zero64 = 0;
    pid = bpf_get_current_pid_tgid();
    time = bpf_ktime_get_ns();

    u64ptr = fcache_start_ts.lookup(&pid);
    if (u64ptr != 0) {
        fcache_fs_start.update(&pid, &time);
    }

    u64ptr = bcache_start_ts.lookup(&pid);
    if (u64ptr != 0) {
        bcache_fs_start.update(&pid, &time);
    }

    u64ptr = search1_start_ts.lookup(&pid);
    if (u64ptr != 0) {
        search1_fs_start.update(&pid, &time);
    }

    // u64ptr = bcache_start_ts.lookup(&pid);
    // if (u64ptr != 0) {
    //     flag = 1;
    // }

    // u64ptr = search1_start_ts.lookup(&pid);
    // if (u64ptr != 0) {
    //     flag = 1;
    // }

    // if (flag != 0) {
    //     memcontrol_start.update(&pid, &time);

    //     u32ptr = memcontrol_num.lookup(&pid);
    //     if (u32ptr == 0) {
    //         memcontrol_num.update(&pid, &zero32);
    //         memcontrol_time.update(&pid, &zero64);
    //     }        
    // }

    return 0;
}

int detect_fs_ret(struct pt_regs *ctx) {
    u32 pid, zero32, *u32ptr;
    u64 *u64ptr, zero64, delta;

    zero32 = 0;
    zero64 = 0;
    pid = bpf_get_current_pid_tgid();

    u64ptr = fcache_fs_start.lookup(&pid);
    if (u64ptr != 0) {
        delta = (bpf_ktime_get_ns() - *u64ptr) / 1000;
        u64ptr = fcache_fs_time.lookup(&pid);
        if (u64ptr != 0) {
            if (delta == 0) delta = 1;
            *u64ptr += delta;
        }
        fcache_fs_start.delete(&pid);
    }

    u64ptr = bcache_fs_start.lookup(&pid);
    if (u64ptr != 0) {
        delta = (bpf_ktime_get_ns() - *u64ptr) / 1000;
        u64ptr = bcache_fs_time.lookup(&pid);
        if (u64ptr != 0) {
            if (delta == 0) delta = 1;
            *u64ptr += delta;
        }
        bcache_fs_start.delete(&pid);
    }

    u64ptr = search1_fs_start.lookup(&pid);
    if (u64ptr != 0) {
        delta = (bpf_ktime_get_ns() - *u64ptr) / 1000;
        u64ptr = search1_fs_time.lookup(&pid);
        if (u64ptr != 0) {
            if (delta == 0) delta = 1;
            *u64ptr += delta;
        }
        search1_fs_start.delete(&pid);
    }
    
    // u64ptr = memcontrol_start.lookup(&pid);
    // if (u64ptr != 0) {
    //     delta = (bpf_ktime_get_ns() - *u64ptr) / 1000;
        
    //     u32ptr = memcontrol_num.lookup(&pid);
    //     if (u32ptr != 0) {
    //         *u32ptr += 1;
    //     }

    //     u64ptr = memcontrol_time.lookup(&pid);
    //     if (u64ptr != 0) {
    //         *u64ptr += delta;
    //     }

    //     memcontrol_start.delete(&pid);
    // }

    return 0;
}
