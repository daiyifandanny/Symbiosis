from bcc import BPF, USDT
from time import sleep
from sys import argv, stdout
from ctypes import c_uint


working_dir = "/home/yifan/research/cache"
bpf_source_path = working_dir + "/bpf/cachestat/leveldb_cachestat.c"
target_path = working_dir + "/leveldb/build/db_bench"
target_path = working_dir +"/bpf/cachestat/test/simple_read"
# target_path = working_dir +"/bpf/cachestat/test/linear"
# target_path = working_dir + "/sqlite/app/simple_read"
# target_path = working_dir + "/mongo/server/build/install/bin/mongod"
# target_path = working_dir + "/wiredtiger/app/simple_read"
# target_path = working_dir + "/rocksdb/build/db_bench"
# target_path = working_dir +"/bpf/cachestat/test/btree_sim"
trace_output_filename = "temp.txt" if len(argv) < 2 else argv[1]
output_fd = stdout if len(argv) < 3 else open(argv[2], "w")


usdt = USDT(path=target_path)
usdt.enable_probe(probe="fcache_start_probe", fn_name="fcache_start")
usdt.enable_probe(probe="fcache_end_probe", fn_name="fcache_end")
usdt.enable_probe(probe="bcache_start_probe", fn_name="bcache_start")
usdt.enable_probe(probe="bcache_end_probe", fn_name="bcache_end")
usdt.enable_probe(probe="search1_start_probe", fn_name="search1_start")
usdt.enable_probe(probe="search1_end_probe", fn_name="search1_end")
usdt.enable_probe(probe="pcache_access1", fn_name="pcache_detect_access1")
usdt.enable_probe(probe="pcache_access2", fn_name="pcache_detect_access2")

bpf = BPF(src_file=bpf_source_path, usdt_contexts=[usdt])
bpf.attach_kprobe(event="lru_cache_add", fn_name="pcache_detect_miss")
bpf.attach_kprobe(event="__delete_from_page_cache", fn_name="pcache_detect_eviction")
bpf.attach_kprobe(event="blk_account_io_start", fn_name="detect_blk")
# bpf.attach_kprobe(event="blk_account_io_done", fn_name="detect_blk_return")

bpf.attach_kprobe(event="page_cache_sync_ra", fn_name="pcache_detect_sync")
bpf.attach_kprobe(event="do_sync_mmap_readahead", fn_name="pcache_detect_sync")
bpf.attach_kprobe(event="page_cache_async_ra", fn_name="pcache_detect_async")
bpf.attach_kretprobe(event="page_cache_sync_ra", fn_name="pcache_detect_sync_ret")
bpf.attach_kretprobe(event="do_sync_mmap_readahead", fn_name="pcache_detect_sync_ret")
bpf.attach_kretprobe(event="page_cache_async_ra", fn_name="pcache_detect_async_ret")
# bpf.attach_kprobe(event="try_to_free_mem_cgroup_pages", fn_name="detect_fs")
# bpf.attach_kretprobe(event="try_to_free_mem_cgroup_pages", fn_name="detect_fs_ret")
# bpf.attach_kprobe(event="workingset_refault", fn_name="detect_activation")
# bpf.attach_kprobe(event="__x64_sys_pread", fn_name="detect_fs")
# bpf.attach_kretprobe(event="__x64_sys_pread", fn_name="detect_fs_ret")


print("Tracing... Hit Ctrl-C to end")
while True:
    try:
        sleep(1)
    except KeyboardInterrupt:
        break


print("\nReporting...")

key = 0
print("fcache_pcache_hit", file=output_fd)
for k, v in bpf["fcache_fs_hit_num"].items():
    if True:
        print("Pid:{} FsHitNum:{} FsHitTime:{} CacheHitNum:{} CacheHitTime:{} CacheMissNum:{} CacheMissTime:{} Activations:{}".format(k, v.value, 
            bpf["fcache_fs_hit_time"][k].value, bpf["fcache_hit_num"][k].value, bpf["fcache_hit_time"][k].value, 
            bpf["fcache_miss_num"][k].value, bpf["fcache_miss_time"][k].value, bpf["fcache_activation_num"][k].value), file=output_fd)
    key = k

print("fcache_pcache_miss", file=output_fd)
for k, v in bpf["fcache_pcache_miss_num"].items():
    if True:
        print("Pid:{} Num:{} Time:{} PageCount:{} PageEvicted:{} Sync:{} Async:{} SyncNum:{} AsyncNum:{}".format(
            k, v.value, bpf["fcache_pcache_miss_time"][k].value, bpf["fcache_pcache_miss_page_count"][k].value,
            bpf["fcache_pcache_evicted_page_count"][k].value, bpf["fcache_sync_count"][k].value, bpf["fcache_async_count"][k].value, 
            bpf["fcache_sync_num"][k].value, bpf["fcache_async_num"][k].value), file=output_fd)

print("bcache_pcache_hit", file=output_fd)
for k, v in bpf["bcache_fs_hit_num"].items():
    if True:
        print("Pid:{} FsHitNum:{} FsHitTime:{} CacheHitNum:{} CacheHitTime:{} CacheMissNum:{} CacheMissTime:{}".format(k, v.value, 
            bpf["bcache_fs_hit_time"][k].value, bpf["bcache_hit_num"][k].value, bpf["bcache_hit_time"][k].value, 
            bpf["bcache_miss_num"][k].value, bpf["bcache_miss_time"][k].value), file=output_fd)
    key = k

print("bcache_pcache_miss", file=output_fd)
for k, v in bpf["bcache_pcache_miss_num"].items():
    if True:
        print("Pid:{} Num:{} Time:{} PageCount:{} PageEvicted:{} Sync:{} Async:{} SyncNum:{} AsyncNum:{}".format(
            k, v.value, bpf["bcache_pcache_miss_time"][k].value, bpf["bcache_pcache_miss_page_count"][k].value,
            bpf["bcache_pcache_evicted_page_count"][k].value, bpf["bcache_sync_count"][k].value, bpf["bcache_async_count"][k].value, 
            bpf["bcache_sync_num"][k].value, bpf["bcache_async_num"][k].value), file=output_fd)

print("search1_pcache_hit", file=output_fd)
for k, v in bpf["search1_fs_hit_num"].items():
    if True:
        print("Pid:{} FsHitNum:{} FsHitTime:{} CacheHitNum:{} CacheHitTime:{} CacheMissNum:{} CacheMissTime:{}".format(k, v.value, 
            bpf["search1_fs_hit_time"][k].value, bpf["search1_hit_num"][k].value, bpf["search1_hit_time"][k].value, 
            bpf["search1_miss_num"][k].value, bpf["search1_miss_time"][k].value), file=output_fd)
    key = k

print("search1_pcache_miss", file=output_fd)
for k, v in bpf["search1_pcache_miss_num"].items():
    if True:
        print("Pid:{} Num:{} Time:{} PageCount:{} PageEvicted:{} Sync:{} Async:{} SyncNum:{} AsyncNum:{}".format(
            k, v.value, bpf["search1_pcache_miss_time"][k].value, bpf["search1_pcache_miss_page_count"][k].value,
            bpf["search1_pcache_evicted_page_count"][k].value, bpf["search1_sync_count"][k].value, bpf["search1_async_count"][k].value, 
            bpf["search1_sync_num"][k].value, bpf["search1_async_num"][k].value), file=output_fd)

for k, v in bpf["pcache_thrashing_count"].items():
    print("page cache readahead thrashing:{}".format(v.value), file=output_fd)

# for k, v in bpf["page_cache_evictions"].items():
#     print("memcg:{} evictions:{}".format(k.value, v.value), file=output_fd)

# for k, v in bpf["memcontrol_num"].items():
#     print("memcontrol Pid:{} Time:{} Num:{}".format(k, bpf["memcontrol_time"][k].value, v.value), file=output_fd)
# print("memcontrol time:{} num:{}".format(bpf["memcontrol_time"][key].value, bpf["memcontrol_num"][key].value), file=output_fd)

# with open("./page_cache.debug", "w") as output_file:
#     pages = list()
#     for k, v in bpf["page_cache"].items():
#         pages.append((k.ino, k.offset))
#     for item in sorted(pages):
#         print(item, file=output_file)

# with open("pc_trace.txt", "w") as output_file:
#     table = bpf["page_cache_trace"]
#     try:
#         while True:
#             value = table.pop()
#             print("{}".format(value.value), file=output_file)
#     except KeyError:
#         pass 

# print("\nSampling...")

# with open(trace_output_filename, "w") as output_file:
#     table = bpf["fcache_pcache_miss_sample"]
#     try:
#         while True:
#             value = table.pop()
#             # if value.page_count != 0:
#             if True:
#                 print("{} {} {} {} {} {} {} {} {}".format(value.arg, 1, value.page_count, value.time, value.evicted_count, 
#                     value.sync_count, value.async_count, value.sync_num, value.async_num), file=output_file)
#     except KeyError:
#         pass

#     table = bpf["bcache_pcache_miss_sample"]
#     try:
#         while True:
#             value = table.pop()
#             if True:
#                 print("{} {} {} {} {} {} {} {} {}".format(2, value.arg, value.page_count, value.time, value.evicted_count, 
#                     value.sync_count, value.async_count, value.sync_num, value.async_num), file=output_file)
#     except KeyError:
#         pass

#     table = bpf["search1_pcache_miss_sample"]
#     try:
#         while True:
#             value = table.pop()
#             if value.page_count != 0:
#                 print("{} {} {} {} {} {} {} {} {}".format(3, value.arg, value.page_count, value.time, value.evicted_count, 
#                     value.sync_count, value.async_count, value.sync_num, value.async_num), file=output_file)
#     except KeyError:
#         pass
