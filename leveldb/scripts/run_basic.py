import subprocess

base_dir = "/home/yifan/research/cache"
working_dir = base_dir + "/levedb"
target = working_dir + "/build/db_bench"
script_dir = working_dir + "/scripts"
result_dir = base_dir + "/results"

basic_command = "cgexec -g memory:{} {} --benchmarks={} --open_files={} " \
                + "--cache_size={} --use_existing_db={} --reads={} " \
                + "| tee {}"

max_open_files = 1048576
db_size = 10 * 1024 * 1024 * 1024
num_entries = 80000000
num_reads = 8000000

memory_limits = [100, 50, 25, 10]
benchmark_types = ["fillrandom", "fillseq", "readseq", "readrandom"]
file_cache_enabled = [True, False]
block_cache_enabled = [True, False]

for memory_limit in memory_limits:
    for benchmark_type in benchmark_types:
        for file_cache in file_cache_enabled:
            for block_cache in block_cache_enabled:
                open_files = max_open_files if file_cache else 0
                cache_size = int(memory_limit / 100 * db_size * 0.9) if block_cache else -1
                use_existing_db = 1 if "read" in benchmark_type else 0
                reads = num_reads
                output_filename = "{}/leveldb_{}_limit-{}_file-{}_block-{}".format(result_dir,
                    benchmark_type, memory_limit, file_cache, block_cache)
                command = basic_command.format(memory_limit, target, benchmark_type, open_files,
                                                cache_size, use_existing_db, reads, output_filename)
                with open(output_filename, "w") as output_file:
                    subprocess.run(command, shell=True)
