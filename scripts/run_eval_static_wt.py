import subprocess


leveldb_command_base = "cgexec -g memory:10 -- ./simple_read --trace ../../traces/{}_10M_{}.out.req.trace \
                        --memory_size {} --cache_size {} --output wt3/{}.latency \
                        | tee wt3/{}.output"
output_filename_base = "{}_{}_{}"

memory_size_mk0 = 1074000000
memory_size_default = 268500000
# memory_size_list = [990000000]
memory_ratio_list = [0.2, 0.4, 0.6, 0.8, 1]
# memory_ratio_list = [1]
workload_list = ["zipfian", "hotspot70", "hotspot80", "hotspot90", "uniform"]
# workload_list = ["hotspot90"]
experiment_target_list = ["adapter", "Mk0", "baseline"]
# experiment_target_list = ["baseline"]
# memory_ratio_list.reverse()

for experiment_target in experiment_target_list:
    for workload in workload_list:
        for memory_ratio in memory_ratio_list:
            memory_size = memory_size_mk0 if experiment_target == "adapter" else 0
            cache_size = memory_size_mk0 if experiment_target == "Mk0" else memory_size_default
            output_filename = output_filename_base.format(experiment_target, workload, memory_ratio)
            leveldb_command = leveldb_command_base.format(workload, memory_ratio, memory_size, cache_size, output_filename, output_filename)
            print(leveldb_command)
            subprocess.run(leveldb_command, shell=True)
