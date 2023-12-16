import subprocess
import time
import os


base_dir = "/home/yifan/research/cache"
working_dir = base_dir + "/simulator"
target = working_dir + "/main.py"
script_dir = base_dir + "/scripts"
result_dir = working_dir + "/results/app_latency2"
bpf = base_dir + "/bpf/cachestat/leveldb_cachestat.py"

simulator_command_base = "python3 {} --memory_size 1 --page_cache_size {} --app_miss_cost {} | tee {}"

output_filename_base = "{}/memory_1_pcsize-{}_appmisscost-{}"


if not os.path.exists(result_dir):
    os.mkdir(result_dir)

pc_sizes = [0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1]
miss_costs = [10, 20, 30, 40, 50, 60, 70, 80, 90, 100]

for miss_cost in miss_costs:
    for pc_size in pc_sizes:
        output_filename = output_filename_base.format(result_dir, pc_size, miss_cost)
        simulator_command = simulator_command_base.format(target, pc_size, miss_cost, output_filename)

        print(simulator_command)
        time.sleep(1)
        subprocess.run(simulator_command, shell=True)
