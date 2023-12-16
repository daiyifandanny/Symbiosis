import subprocess
import time
from typing import SupportsRound


base_dir = "/home/yifan/research/cache"
working_dir = base_dir + "/sqlite"
target = working_dir + "/app/simple_read"
script_dir = base_dir + "/scripts"
result_dir = base_dir + "/results/sqlite_cachestat_pcsize_mmap"
bpf = base_dir + "/bpf/cachestat/leveldb_cachestat.py"

sqlite_basic_command = "cgexec -g memory:{} {} -r --cache_size={} " \
                + "| tee {}"
preparation_command = "sync; echo 3 | sudo tee /proc/sys/vm/drop_caches; sudo fstrim -av"
bpf_basic_command = "sudo python3 {} {} {}"

output_filename = "{}/sqlite_limit-{}_pcsize-{}.{}"


memory_limits = [100, 10, 1]
cache_size_lists = [
    [x * 100000 for x in [9, 8, 7, 6, 5, 4, 3, 2, 1, 0]],
    [x * 100000 for x in [9, 8, 7, 6, 5, 4, 3, 2, 1, 0]],
    [x * 10000 for x in [8, 7, 6, 5, 4, 3, 2, 1, 0]]
]

for memory_limit, cache_sizes in zip(memory_limits, cache_size_lists):
    for cache_size in cache_sizes:
        sqlite_output_filename = output_filename.format(result_dir, memory_limit * 10, cache_size, "sqlout")
        sqlite_command = sqlite_basic_command.format(memory_limit, target, cache_size, sqlite_output_filename)
        bpf_output_filename = output_filename.format(result_dir, memory_limit * 10, cache_size, "bpfout")
        bpf_trace_output_filename = output_filename.format(result_dir, memory_limit * 10, cache_size, "trace")
        bpf_command = bpf_basic_command.format(bpf, bpf_trace_output_filename, bpf_output_filename)

        print(sqlite_command)
        print(bpf_command)
        time.sleep(1)
        bpf_process = subprocess.Popen(bpf_command, shell=True)
        time.sleep(5)
        subprocess.run(sqlite_command, shell=True)
        kill_command = "sudo kill -2 {}".format(bpf_process.pid + 2)
        subprocess.run(kill_command, shell=True)
        time.sleep(5)
