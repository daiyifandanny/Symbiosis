import subprocess
import time
import os


base_dir = "/home/yifan/research/cache"
working_dir = base_dir + "/bpf/cachestat/test"
target = working_dir + "/simple_read"
script_dir = base_dir + "/scripts"
result_dir = base_dir + "/results/simple_memory3"
bpf = base_dir + "/bpf/cachestat/leveldb_cachestat.py"

micro_basic_command = "cgexec -g memory:10 {} -r --distribution={} --size_factor={}" \
                + " | tee {}"
preparation_command = "sync; echo 3 | sudo tee /proc/sys/vm/drop_caches; sudo fstrim -av"
bpf_basic_command = "sudo python3 {} {} {}"

output_filename = "{}/simple_size-{}_distribution-{}.{}"


if not os.path.exists(result_dir):
    os.mkdir(result_dir)

size_factors = [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1]
distributions = [0, 1]

for distribution in distributions:
    for size_factor in size_factors:
        micro_output_filename = output_filename.format(result_dir, size_factor, distribution, "micro")
        micro_command = micro_basic_command.format(target, distribution, size_factor, micro_output_filename)
        bpf_output_filename = output_filename.format(result_dir, size_factor, distribution, "bpfout")
        bpf_trace_output_filename = output_filename.format(result_dir, size_factor, distribution, "trace")
        bpf_command = bpf_basic_command.format(bpf, bpf_trace_output_filename, bpf_output_filename)

        print(micro_command)
        print(bpf_command)
        time.sleep(1)
        bpf_process = subprocess.Popen(bpf_command, shell=True)
        time.sleep(5)
        subprocess.run(micro_command, shell=True)
        kill_command = "sudo kill -2 {}".format(bpf_process.pid + 2)
        subprocess.run(kill_command, shell=True)

for distribution in distributions:
    for size_factor in size_factors:
        micro_output_filename = output_filename.format(result_dir, size_factor, distribution, "micro")
        micro_command = micro_basic_command.format(target, distribution, size_factor, micro_output_filename)

        print(micro_command)
        time.sleep(1)
        subprocess.run(micro_command, shell=True)
