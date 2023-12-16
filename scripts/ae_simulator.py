import subprocess
import time
import os


result_dir = "ae_simulator"

simulator_command_base = "python3 {} --memory_size {} --page_cache_size {} --app_miss_cost {} --ratio {} " + \
                        "--distribution {} | tee {}"

output_filename_base = "{}/memory-{}_pcsize-{}_appmisscost-{}_ratio-{}_distribution-{}.txt"


if not os.path.exists(result_dir):
    os.mkdir(result_dir)

memory_sizes = [0.05, 0.1, 0.15, 0.2, 0.25, 0.3, 0.35, 0.4, 0.45, 0.55, 0.6, 0.65, 0.7, 0.75, 0.8, 0.85, 0.9, 0.95, 1]
# memory_sizes = [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.1]
memory_sizes = [0.5]
# ratios = [0.05, 0.1, 0.15, 0.2, 0.25, 0.3, 0.35, 0.4, 0.45, 0.5, 0.55, 0.6, 0.65, 0.7, 0.75, 0.8, 0.85, 0.9, 0.95, 1]
ratios = [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1]
ratios = [0.1, 0.2, 0.3, 0.4, 0.5]
# ratios = [0.5]
miss_costs = [10, 20, 30, 40, 50, 60, 70, 80, 90, 100, 5, 15, 25, 35, 45, 55, 65, 75, 85, 95]
miss_costs = [10]

distributions = [1]
pc_sizes = [0, 0.05, 0.1, 0.15, 0.2, 0.25, 0.3, 0.35, 0.4, 0.45, 0.5, 0.55, 0.6, 0.65, 0.7, 0.75, 0.8, 0.85, 0.9, 0.95, 1]
# pc_sizes = [0]
memory_sizes.reverse()

for distribution in distributions:
    for miss_cost in miss_costs:
        for memory_size in memory_sizes:
            for ratio in ratios:
                pc_size_list = pc_sizes.copy()
                if memory_size > ratio:
                    pc_size_list.append(ratio / memory_size)
                
                for pc_size in pc_size_list:
                    pc_size = round(pc_size * memory_size, 4)
                    output_filename = output_filename_base.format(result_dir, memory_size, pc_size, miss_cost, ratio, distribution)
                    simulator_command = simulator_command_base.format("main.py", memory_size, pc_size, miss_cost, ratio, distribution, output_filename)

                    print(simulator_command)
                    time.sleep(1)
                    subprocess.run(simulator_command, shell=True)
