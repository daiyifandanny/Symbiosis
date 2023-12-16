import subprocess
import time
import os


base_dir = "/home/yifan/research/cache"
working_dir = base_dir + "/rocksdb"
target = working_dir + "/build/db_bench"
script_dir = base_dir + "/scripts"
result_dir = base_dir + "/results/rocksdb_rowcache2"
bpf = base_dir + "/bpf/cachestat/leveldb_cachestat.py"

rocksdb_basic_command = "cgexec -g memory:{} {} --compression_type=none --benchmarks='readrandom' --use_existing_db" \
                + " --db=/nvme/rocksdb --num=10000000 --reads={} --advise_random_on_open --row_cache_size={}" \
                + " | tee {}"
preparation_command = "sync; echo 3 | sudo tee /proc/sys/vm/drop_caches; sudo fstrim -av"
bpf_basic_command = "sudo python3 {} {} {}"

output_filename = "{}/rocksdb_limit-{}_rc-{}.{}"


if not os.path.exists(result_dir):
    os.mkdir(result_dir)

# memory_limits = [100, 10, 1]
# cache_size_lists = [
#     [x * 100000000 for x in [9, 8, 7, 6, 5, 4, 3, 2, 1, 0]],
#     [x * 100000000 for x in [9, 8, 7, 6, 5, 4, 3, 2, 1, 0]],
#     [x * 10000000 for x in [7, 6, 5, 4, 3, 2, 1, 0]]
# ]

memory_limits = [100, 10]
cache_size_lists = [
    [x * 100000000 for x in [9, 8, 7, 6, 5, 4, 3, 2, 1, 0]],
    [x * 100000000 for x in [9, 8, 7, 6, 5, 4, 3, 2, 1, 0]]
]



for memory_limit, cache_sizes in zip(memory_limits, cache_size_lists):
    for cache_size in cache_sizes:
        num_reads = 1000000 if memory_limit == 1 else 10000000
        rocksdb_output_filename = output_filename.format(result_dir, memory_limit / 10, cache_size, "rdb")
        rocksdb_command = rocksdb_basic_command.format(memory_limit, target, num_reads, cache_size, rocksdb_output_filename)
        bpf_output_filename = output_filename.format(result_dir, memory_limit / 10, cache_size, "bpfout")
        bpf_trace_output_filename = output_filename.format(result_dir, memory_limit / 10, cache_size, "trace")
        bpf_command = bpf_basic_command.format(bpf, bpf_trace_output_filename, bpf_output_filename)

        print(rocksdb_command)
        print(bpf_command)
        time.sleep(1)
        # bpf_process = subprocess.Popen(bpf_command, shell=True)
        # time.sleep(5)
        subprocess.run(rocksdb_command, shell=True)
        # for i in range(2, 5):
        #     kill_command = "sudo kill -2 {}".format(bpf_process.pid + i)
        #     subprocess.run(kill_command, shell=True)
        time.sleep(5)
