import subprocess
import shutil

try:
    shutil.rmtree("/nvme/leveldb-write")
except:
    pass
shutil.copytree("/nvme/leveldb3", "/nvme/leveldb-write")

leveldb_command_base = "cgexec -g memory:10 -- ./db_bench --benchmarks=writetrace --use_existing_db=1 \
                        --memory_size={} --cache_size={} --output=statictest/{}.latency --db=/nvme/leveldb-write \
                        --trace1=../../traces/{}_10M_{}.out.req.trace | tee statictest/{}.output"
output_filename_base = "{}_snappy_{}_{}"

memory_size_list = [975000000, 985000000, 990000000, 990000000, 990000000]
# memory_size_list = [990000000]
memory_ratio_list = [0.2, 0.4, 0.6, 0.8, 1]
# memory_ratio_list = [1]
workload_list = ["uniform", "zipfian", "hotspot70", "hotspot80", "hotspot90"]
workload_list = ["uniform"]
experiment_target_list = ["adapter", "Mk0", "baseline"]
memory_ratio_list.reverse()
memory_size_list.reverse()

for experiment_target in experiment_target_list:
    for workload in workload_list:
        for index_ratio, memory_ratio in enumerate(memory_ratio_list):
            memory_size = memory_size_list[index_ratio] if experiment_target == "adapter" else 0
            cache_size = memory_size_list[index_ratio] if experiment_target == "Mk0" else 8388608
            output_filename = output_filename_base.format(experiment_target, workload, memory_ratio)
            leveldb_command = leveldb_command_base.format(memory_size, cache_size, output_filename, workload, memory_ratio,
                                                            output_filename)
            print(leveldb_command)
            subprocess.run(leveldb_command, shell=True)
