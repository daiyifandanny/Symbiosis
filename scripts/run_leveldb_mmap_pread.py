import subprocess
import time
import os

base_dir = "/home/yifan/research/cache"
working_dir = base_dir + "/leveldb"
target = working_dir + "/build/db_bench"
script_dir = base_dir + "/scripts"
result_dir = base_dir + "/results/leveldb_mmap_pread"

leveldb_basic_command = "MMAP_LIMIT={} cgexec -g memory:{} {} --benchmarks=readrandom --open_files=50000 " \
                + "--use_existing_db=1 --reads=1000000" \
                + "| tee {}"

output_filename = "{}/leveldb_limit-{}_mmap-{}.{}"

max_open_files = 50000

memory_limits = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]

if not os.path.exists(result_dir):
    os.mkdir(result_dir)

for memory_limit in memory_limits:
    for mmap in [True, False]:
        mmap_limit = max_open_files if mmap else 0

        leveldb_output_filename = output_filename.format(result_dir,
                                    memory_limit, mmap, "dbout")

        # leveldb_command = leveldb_basic_command.format(0, 100, target, "temp.txt")
        # subprocess.run(leveldb_command, shell=True)

        leveldb_command = leveldb_basic_command.format(mmap_limit, memory_limit, target, leveldb_output_filename)
        print(leveldb_command)
        subprocess.run(leveldb_command, shell=True)
        time.sleep(5)
