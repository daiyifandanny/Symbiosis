import subprocess
import time
import os


base_dir = "/home/yifan/research/cache"
working_dir = base_dir + "/rocksdb"
target = working_dir + "/build/db_bench"
script_dir = base_dir + "/scripts"
result_dir = base_dir + "/results/rocksdb_advise"
bpf = base_dir + "/bpf/cachestat/leveldb_cachestat.py"

rocksdb_basic_command = "cgexec -g memory:{} {} --compression_type=none --benchmarks='readrandom' --use_existing_db" \
                + " --db=/nvme/rocksdb --num=10000000 --reads=1000000 {}" \
                + " | tee {}"
preparation_command = "sync; echo 3 | sudo tee /proc/sys/vm/drop_caches; sudo fstrim -av"
bpf_basic_command = "sudo python3 {} {} {}"

output_filename = "{}/rocksdb_limit-{}_{}.{}"


if not os.path.exists(result_dir):
    os.mkdir(result_dir)

# memory_limits = [100, 10, 1]
# cache_size_lists = [
#     [x * 100000000 for x in [9, 8, 7, 6, 5, 4, 3, 2, 1, 0]],
#     [x * 100000000 for x in [9, 8, 7, 6, 5, 4, 3, 2, 1, 0]],
#     [x * 10000000 for x in [7, 6, 5, 4, 3, 2, 1, 0]]
# ]

memory_limits = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
advices = ["", "--advise_random_on_open"]

for advice in advices:
    for memory_limit in memory_limits:
        filename_adv = "normal" if advice == "" else "random"
        rocksdb_output_filename = output_filename.format(result_dir, memory_limit, filename_adv, "rdb")
        rocksdb_command = rocksdb_basic_command.format(memory_limit, target, advice, rocksdb_output_filename)

        print(rocksdb_command)
        time.sleep(1)
        subprocess.run(rocksdb_command, shell=True)
        time.sleep(5)
