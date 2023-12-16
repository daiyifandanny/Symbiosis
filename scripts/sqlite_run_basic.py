import subprocess
import time

base_dir = "/home/yifan/research/cache"
working_dir = base_dir + "/sqlite"
script_dir = base_dir + "/scripts"
result_dir = base_dir + "/results"
target = script_dir + "/sqlite_app.py"


basic_command = "cgexec -g memory:{} python3 {} --benchmark={} --cache_size={} --page_size={} \
                    | tee {}"

db_size = 10 * 1024 * 1024 * 1024

memory_limits = [100, 50, 25, 10]
page_sizes = [4096, 1024, 16384]
benchmarks = ["fillrandom", "fillseq", "readseq", "readrandom"]
cache_size_ratios = [0.75, 0.5, 0.01]

for page_size in page_sizes:
    for memory_limit in memory_limits:
        for benchmark in benchmarks:
            for cache_size_ratio in cache_size_ratios:
                cache_size = int(memory_limit / 100 * db_size * 0.9 / 1024 * cache_size_ratio)
                output_filename = "{}/sqlite_{}_limit-{}_page-{}_cache-ratio-{}".format(result_dir,
                    benchmark, memory_limit, page_size, cache_size_ratio)
                command = basic_command.format(memory_limit, target, benchmark, cache_size, page_size, output_filename)
                print(command)
                time.sleep(1)
                subprocess.run(command, shell=True)
