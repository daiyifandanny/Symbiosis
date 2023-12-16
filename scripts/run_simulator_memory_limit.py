import subprocess
import time
import os


base_dir = "/home/yifan/research/cache"
working_dir = base_dir + "/simulator"
target = working_dir + "/main.py"
script_dir = base_dir + "/scripts"
result_dir = base_dir + "/results/simple_memory2"
bpf = base_dir + "/bpf/cachestat/leveldb_cachestat.py"

simulator_command_base = "python3 {} --memory_size {} --page_cache_size {} --max_pages {} --distribution {} --ratio 1 --trace {} | tee {}"

output_filename_base = "{}/size-{}_distribution-{}.sim"


if not os.path.exists(result_dir):
    os.mkdir(result_dir)

size_factors = [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1]
distributions = [0, 1]

for distribution in distributions:
    for size_factor in size_factors:
        max_pages = int(262144 / size_factor)
        output_filename = output_filename_base.format(result_dir, size_factor, distribution)
        simulator_command = simulator_command_base.format(target, size_factor, size_factor, max_pages, distribution, 
                                                          f"{distribution}_{size_factor}.trace", output_filename)
        print(simulator_command)
        time.sleep(1)
        subprocess.run(simulator_command, shell=True)
