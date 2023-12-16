import subprocess
import time
import os


base_dir = "/home/yifan/research/cache"
working_dir = base_dir + "/bpf/cachestat/test"
target = working_dir + "/btree_sim"
script_dir = base_dir + "/scripts"
result_dir = base_dir + "/results/btreesim_cachestat_focusratio2"
bpf = base_dir + "/bpf/cachestat/leveldb_cachestat.py"

micro_basic_command = "cgexec -g memory:{} {} -r --focus_ratio={} -a 256 --read_size=8192" \
                + " | tee {}"
preparation_command = "sync; echo 3 | sudo tee /proc/sys/vm/drop_caches; sudo fstrim -av"
bpf_basic_command = "sudo python3 {} {} {}"

output_filename = "{}/btreesim_limit-{}_ratio-{}.{}"


if not os.path.exists(result_dir):
    os.mkdir(result_dir)

memory_limits = [7, 8, 9, 10, 1, 2, 3, 4, 5, 6]
focus_ratios = [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9]

for memory_limit in memory_limits:
    for focus_ratio in focus_ratios:
        micro_output_filename = output_filename.format(result_dir, memory_limit / 10, focus_ratio, "micro")
        micro_command = micro_basic_command.format(memory_limit, target, focus_ratio, micro_output_filename)
        bpf_output_filename = output_filename.format(result_dir, memory_limit / 10, focus_ratio, "bpfout")
        bpf_trace_output_filename = output_filename.format(result_dir, memory_limit / 10, focus_ratio, "trace")
        bpf_command = bpf_basic_command.format(bpf, bpf_trace_output_filename, bpf_output_filename)

        print(micro_command)
        print(bpf_command)
        time.sleep(1)
        bpf_process = subprocess.Popen(bpf_command, shell=True)
        time.sleep(5)
        subprocess.run(micro_command, shell=True)
        kill_command = "sudo kill -2 {}".format(bpf_process.pid + 2)
        subprocess.run(kill_command, shell=True)
        time.sleep(5)
