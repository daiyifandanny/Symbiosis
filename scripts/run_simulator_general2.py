#! /usr/bin/env python3
# Set 1:
# arg1 = memory_ratio = 0.1,0.15,...,.0.95,1 (19 items)
# arg2 = compression_ratio = 0.1,0.15,...,.0.95,1 (19 items)
# arg3 = miss_cost = 10,50,100 (3 items)
# arg4 = distribution = 0,1 (2 items)

# Set 2:
# arg1 = 0.8 arg2 = 0.5 arg4 = 0
# arg3 = 5,10,...,95,100 (20 items)

import subprocess
import time
import os
import sys


CACHESTAT_ROOT_DIR = os.getenv("CACHESTAT_ROOT_DIR")
if CACHESTAT_ROOT_DIR is None:
    print('CACHESTAT_ROOT_DIR environment variable does not exist. Please source or relogin')
    print('Remember to run the setup_cache_sim.sh though')
    sys.exit(1)

base_dir = CACHESTAT_ROOT_DIR
working_dir = base_dir + "/simulator"
target = working_dir + "/main.py"
script_dir = base_dir + "/scripts"
result_dir = working_dir + "/results/best_cache_size2"
bpf = base_dir + "/bpf/cachestat/leveldb_cachestat.py"

simulator_command_base = "python3 {} --memory_size {} --page_cache_size {} --app_miss_cost {} --ratio {} " + \
                        "--distribution {} --max_pages {} | tee {}"

output_filename_base = "{}/memory_ratio-{}_pcsize-{}_appmisscost-{}_ratio-{}_distribution-{}.txt"


if not os.path.exists(result_dir):
    os.mkdir(result_dir)

# memory_sizes = [0.05, 0.1, 0.15, 0.2, 0.25, 0.3, 0.35, 0.4, 0.45, 0.55, 0.6, 0.65, 0.7, 0.75, 0.8, 0.85, 0.9, 0.95, 1]
# # memory_sizes = [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.1]
# memory_sizes = [0.5]
# ratios = [0.05, 0.1, 0.15, 0.2, 0.25, 0.3, 0.35, 0.4, 0.45, 0.5, 0.55, 0.6, 0.65, 0.7, 0.75, 0.8, 0.85, 0.9, 0.95, 1]
# ratios = [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1]
# ratios = [0.1, 0.2, 0.3, 0.4, 0.5]
# # ratios = [0.5]
# miss_costs = [10, 20, 30, 40, 50, 60, 70, 80, 90, 100, 5, 15, 25, 35, 45, 55, 65, 75, 85, 95]
# miss_costs = [50]

if len(sys.argv) < 5:
    print("python3 script_path.py max_pages_list ratio_list miss_cost_list distribution_list")
    print("Each list is a string with numbers, comma separated, e.g. 1,2,3")
    print('    Optional arg: [trace:{name of trace}]')
    exit(1)

memory_ratio_list = [float(x) for x in sys.argv[1].split(",")]
ratio_list = [float(x) for x in sys.argv[2].split(",")]
miss_cost_list = [int(x) for x in sys.argv[3].split(",")]
distribution_list = [int(x) for x in sys.argv[4].split(",")]
# num_reads_list = [10000000, 25000000]
pc_sizes = [0, 0.05, 0.1, 0.15, 0.2, 0.25, 0.3, 0.35, 0.4, 0.45, 0.5, 0.55, 0.6, 0.65, 0.7, 0.75, 0.8, 0.85, 0.9, 0.95, 1]
# pc_sizes = [0]
# memory_sizes.reverse()

trace_name = None
# do we have trace to use?
for cur_arg in sys.argv:
    if 'trace:' in cur_arg:
        trace_name = cur_arg[6:]
        print(trace_name)

MAX_KEY_IN_TRACE = 0
with open(trace_name) as tf_r:
    for line in tf_r:
        line = line.strip()
        key = int(line)
        if key > MAX_KEY_IN_TRACE:
            MAX_KEY_IN_TRACE = key
print(f'MAX_KEY_IN_TRACE:{MAX_KEY_IN_TRACE}')

for distribution in distribution_list:
    for miss_cost in miss_cost_list:
        for memory_ratio in memory_ratio_list:
            for ratio in ratio_list:
                pc_size_list = pc_sizes.copy()
                memory_size = memory_ratio
                # num_reads = num_reads_list[distribution]
                max_pages = int(262144 / memory_ratio)
                if memory_size > ratio:
                    pc_size_list.append(ratio / memory_size)

                for pc_size in pc_size_list:
                    pc_size = round(pc_size * memory_size, 4)
                    output_filename = output_filename_base.format(result_dir, memory_ratio, pc_size, miss_cost, ratio, distribution)
                    simulator_command = simulator_command_base.format(target, memory_size, pc_size, miss_cost, \
                            ratio, distribution, max_pages, output_filename)
                    if trace_name is not None:
                        cur_simulator_command_base = simulator_command_base.replace('--max_pages', \
                                '--trace {} --max_pages')
                        simulator_command = cur_simulator_command_base.format(target, memory_size, pc_size, miss_cost, \
                                ratio, distribution, trace_name, max_pages, output_filename)

                    if MAX_KEY_IN_TRACE > max_pages:
                        print(simulator_command, file=sys.stderr)
                        print(f'MAX_KEY:{MAX_KEY_IN_TRACE} max_pages:{max_pages}', file=sys.stderr)
                        raise RuntimeError(f'MAX PAGES!')
                    print(simulator_command)
                    time.sleep(1)
                    subprocess.run(simulator_command, shell=True)
