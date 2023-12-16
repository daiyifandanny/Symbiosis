import subprocess
import time
import os

base_dir = "/home/yifan/research/cache"
working_dir = base_dir + "/leveldb"
target = working_dir + "/build/db_bench"
script_dir = base_dir + "/scripts"
result_dir = base_dir + "/results/leveldb_doublecaching"

leveldb_basic_command = "MMAP_LIMIT=0 cgexec -g memory:10 {} --benchmarks=readrandom --open_files=50000 " \
                + "--use_existing_db=1 --reads=1000000 --cache_size={} --num={}" \
                + "| tee {}"

output_filename = "{}/leveldb_ws-{}_cache-{}.{}"

max_open_files = 50000

nums = [10, 2, 5, 20]
cache_sizes = [9.5, 9, 8, 7, 6, 5, 4, 3, 2, 1, 0]

nums = [20]
cache_sizes = [4, 5, 6, 7, 8, 9, 9.5]

if not os.path.exists(result_dir):
    os.mkdir(result_dir)

# fill_command = "{} --benchmarks=fillseq --num={}".format(target, 20000000)
# subprocess.run(fill_command, shell=True)
for num in nums:
    for cache_size in cache_sizes:
        leveldb_output_filename = output_filename.format(result_dir,
                                    num, cache_size, "dbout")

        # leveldb_command = leveldb_basic_command.format(target, 0, "temp.txt")
        # subprocess.run(leveldb_command, shell=True) 

        leveldb_command = leveldb_basic_command.format(target, int(cache_size * 100 * 1024 * 1024), num * 1000000,leveldb_output_filename)
        print(leveldb_command)
        subprocess.run(leveldb_command, shell=True)
        time.sleep(5)
