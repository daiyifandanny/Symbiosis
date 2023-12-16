import subprocess
import time
from typing import SupportsRound


base_dir = "/home/yifan/research/cache"
working_dir = base_dir + "/leveldb"
target = working_dir + "/build/db_bench"
script_dir = base_dir + "/scripts"
result_dir = base_dir + "/results/leveldb_cachestat3"
bpf = base_dir + "/bpf/cachestat/leveldb_cachestat.py"

leveldb_basic_command = "MMAP_LIMIT={} cgexec -g memory:{} {} --benchmarks={} --open_files={} " \
                + "--cache_size={} --use_existing_db={} --reads={} --num={} " \
                + "| tee {}"
preparation_command = "sync; echo 3 | sudo tee /proc/sys/vm/drop_caches; sudo fstrim -av"
bpf_basic_command = "sudo python3 {} {} {}"

output_filename = "{}/leveldb_{}_limit-{}_file-{}_block-{}_mmap-{}.{}"

max_open_files = 50000
db_size = 10 * 1024 * 1024 * 1024
num_entries = 80000000
num_reads = 8000000

benchmark_types = ["readrandom", "readseq"]
memory_limits = [100, 50, 10]
file_cache_enabled = [True, False]
block_cache_enabled = [True, False]
mmap_enabled = [True, False]



for benchmark_type in benchmark_types:
    for memory_limit in memory_limits:    
        for file_cache in file_cache_enabled:
            for block_cache in block_cache_enabled:
                for mmap in mmap_enabled:

                    if mmap and block_cache:
                        continue

                    open_files = max_open_files if file_cache else 0
                    cache_size = int(memory_limit / 100 * db_size * 0.9) if block_cache else -1
                    mmap_limit = 50000 if mmap else 0
                    use_existing_db = 1 if "read" in benchmark_type else 0

                    leveldb_output_filename = output_filename.format(result_dir,
                                                benchmark_type, memory_limit, file_cache, block_cache, mmap, "dbout")
                    leveldb_command = leveldb_basic_command.format(mmap_limit, memory_limit, target, benchmark_type, open_files,
                                                    cache_size, use_existing_db, num_reads, num_entries, leveldb_output_filename)

                    bpf_output_filename = output_filename.format(result_dir,
                                                benchmark_type, memory_limit, file_cache, block_cache, mmap, "bpfout")
                    bpf_trace_output_filename = output_filename.format(result_dir,
                                                benchmark_type, memory_limit, file_cache, block_cache, mmap, "trace")
                    bpf_command = bpf_basic_command.format(bpf, bpf_trace_output_filename, bpf_output_filename)
                    
                    print(leveldb_command)
                    print(bpf_command)
                    time.sleep(1)
                    subprocess.run(preparation_command, shell=True)

                    bpf_process = subprocess.Popen(bpf_command, shell=True)
                    time.sleep(5)
                    subprocess.run(leveldb_command, shell=True)
                    kill_command = "sudo kill -2 {}".format(bpf_process.pid + 2)
                    subprocess.run(kill_command, shell=True)
                    time.sleep(5)
