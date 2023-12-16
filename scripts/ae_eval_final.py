import subprocess
import os


if not os.path.exists("ae_final"):
    os.mkdir("ae_final")


leveldb_command_base = "./db_bench --benchmarks=readtrace --use_existing_db=1 " + \
                        "--memory_size={} --cache_size={} --output=ae_final/{} --db=leveldb " + \
                        "--trace1=../../traces/{}.trace --trace2=../../traces/{}.trace " + \
                        "--trace3=../../traces/{}.trace --trace4=../../traces/{}.trace " + \
                        " | tee ae_final/{}"
output_filename_base = "{}_final.{}"


memory_size_list = [975000000]
experiment_target_list = ["adapter", "Mk0", "baseline"]
# experiment_target_list = ["adapter", "Mk0", "baseline"]
traces = ["rocksdb_default_5G", "rocksdb_default_2.5G", "rocksdb_2hotspot2_2.5G", "rocksdb_2hotspot2_5G"]
# traces.reverse()


for index_target, experiment_target in enumerate(experiment_target_list):
    # if index_db_size != 1 or index_name != 0:
    #     continue
    output_filename = output_filename_base.format(experiment_target, "output")
    latency_filename = output_filename_base.format(experiment_target, "latency")
    memory_size = memory_size_list[0] if experiment_target == "adapter" else 0
    cache_size = memory_size_list[0] if experiment_target == "Mk0" else 8388608
    leveldb_command = leveldb_command_base.format(memory_size, cache_size, latency_filename, 
                                                    traces[0], traces[1], traces[2], traces[3], output_filename)
    print(leveldb_command)
    subprocess.run(leveldb_command, shell=True)
