import subprocess
import os



if not os.path.exists("ae_dynamic_latency"):
    os.mkdir("ae_dynamic_latency")
if not os.path.exists("ae_dynamic_output"):
    os.mkdir("ae_dynamic_output")


leveldb_command_base = "./db_bench --benchmarks=readtrace --use_existing_db=1 " + \
                        "--memory_size={} --cache_size={} --output=ae_dynamic_latency/{} --db=leveldb " + \
                        "--trace1=../../traces/{}.trace " + \
                        "--trace2=../../traces/{}.trace | tee ae_dynamic_output/{}"
output_filename_base = "{}_dyn_{}_{}G_{}.txt"


memory_size_list = [960000000, 960000000]
database_size_list = [2, 5]
experiment_name_list = ["uniform-wss", "zipfian-wss", "hotspot-wss", "hotspot-hotspot", "hotspot-hotness"]
workload1_list = [("uniform_10M_1.out.req", "uniform_10M_2G_req"), ("zipfian_10M_1.out.req", "sczipf80_10M_2G_req"), 
                    ("hotspot80_10M_1.out.req", "hotspot80_10M_2G_req"), ("hotspot80_10M_2G_req", "hotspot80_10M_2G_req_m"),
                    ("hotspot90_10M_2G_req", "hotspot70_10M_2G_req_m")]
workload2_list = [("uniform_10M_0.4.out.req", "uniform_10M_0.2.out.req"), ("zipfian_10M_0.4.out.req", "zipfian_10M_0.2.out.req"), 
                    ("hotspot80_10M_0.4.out.req", "hotspot80_10M_0.2.out.req"), ("hotspot80_10M_0.2.out.req", "hotspot80_10M_5G_req_m"),
                    ("hotspot90_10M_0.2.out.req", "hotspot70_10M_5G_req_m")]
workload_list = [workload1_list, workload2_list]
experiment_target_list = ["adapter", "baseline", "Mk0"]
experiment_target_list = ["adapter", "baseline"]
workload_order_list = ["wssup", "wssdown"]
# workload_order_list = ["wssup"]

# experiment_name_list.reverse()
# workload1_list.reverse()
# workload2_list.reverse()

for index_target, experiment_target in enumerate(experiment_target_list):
    for index_name, experiment_name in enumerate(experiment_name_list):
        for index_db_size, db_size in enumerate(database_size_list):

            # if not (index_db_size != 0 or not (index_name == 0 or index_name == 1 or index_name == 2)):
            #     continue

            trace1 = workload_list[index_db_size][index_name][0]
            trace2 = workload_list[index_db_size][index_name][1]
            memory_size = memory_size_list[index_db_size] if experiment_target == "adapter" else 0
            cache_size = memory_size_list[index_db_size] if experiment_target == "Mk0" else 8388608
            for index_order, workload_order in enumerate(workload_order_list):
                output_filename = output_filename_base.format(experiment_target, experiment_name, db_size, workload_order)
                if index_order == 1:
                    trace1, trace2 = trace2, trace1
                leveldb_command = leveldb_command_base.format(memory_size, cache_size, output_filename, trace1, trace2, output_filename)
                print(leveldb_command)
                subprocess.run(leveldb_command, shell=True)
