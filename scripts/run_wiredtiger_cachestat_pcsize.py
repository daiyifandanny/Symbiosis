import subprocess
import time
from typing import SupportsRound


base_dir = "/home/yifan/research/cache"
working_dir = base_dir + "/wiredtiger"
target = working_dir + "/app/simple_read"
script_dir = base_dir + "/scripts"
result_dir = base_dir + "/results/wiredtiger_cachestat_pcsize2"
bpf = base_dir + "/bpf/cachestat/leveldb_cachestat.py"

wiredtiger_basic_command = "cgexec -g memory:{} {} -r --cache_size={} " \
                + "| tee {}"
preparation_command = "sync; echo 3 | sudo tee /proc/sys/vm/drop_caches; sudo fstrim -av"
bpf_basic_command = "sudo python3 {} {} {}"

output_filename = "{}/wiredtiger_limit-{}_pcsize-{}.{}"


memory_limits = [100, 10, 1]
cache_size_lists = [
    [x * 10000 for x in [116, 104, 92, 80, 68, 56, 45, 33, 22, 10]],
    [x * 10000 for x in [116, 104, 92, 80, 68, 56, 45, 33, 22, 10]],
    [x * 10000 for x in [9, 8, 7, 6, 5, 4, 3, 2, 1]]
]

theoretical_cache_size_lists = [
    [x * 100000 for x in [10, 9, 8, 7, 6, 5, 4, 3, 2, 1]],
    [x * 100000 for x in [10, 9, 8, 7, 6, 5, 4, 3, 2, 1]],
    [x * 10000 for x in [9, 8, 7, 6, 5, 4, 3, 2, 1]]
]

for memory_limit, cache_sizes, theoretical_cache_sizes in zip(memory_limits, cache_size_lists, theoretical_cache_size_lists):
    for cache_size, theoretical_cache_size in zip(cache_sizes, theoretical_cache_sizes):
        wiredtiger_output_filename = output_filename.format(result_dir, memory_limit / 10, theoretical_cache_size, "wtout")
        wiredtiger_command = wiredtiger_basic_command.format(memory_limit, target, cache_size, wiredtiger_output_filename)
        bpf_output_filename = output_filename.format(result_dir, memory_limit / 10, theoretical_cache_size, "bpfout")
        bpf_trace_output_filename = output_filename.format(result_dir, memory_limit / 10, theoretical_cache_size, "trace")
        bpf_command = bpf_basic_command.format(bpf, bpf_trace_output_filename, bpf_output_filename)

        print(wiredtiger_command)
        print(bpf_command)
        time.sleep(1)
        bpf_process = subprocess.Popen(bpf_command, shell=True)
        time.sleep(5)
        subprocess.run(wiredtiger_command, shell=True)
        kill_command = "sudo kill -2 {}".format(bpf_process.pid + 2)
        subprocess.run(kill_command, shell=True)
        time.sleep(5)
