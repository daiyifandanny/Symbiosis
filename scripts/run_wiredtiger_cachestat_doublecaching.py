import subprocess
import time
from typing import SupportsRound


base_dir = "/home/yifan/research/cache"
working_dir = base_dir + "/wiredtiger"
target = working_dir + "/app/simple_read"
script_dir = base_dir + "/scripts"
result_dir = base_dir + "/results/wiredtiger_cachestat_doublecaching3"
bpf = base_dir + "/bpf/cachestat/leveldb_cachestat.py"

wiredtiger_basic_command = "cgexec -g memory:{} {} -r --cache_size={} --read_ratio={} " \
                + "| tee {}"
preparation_command = "sync; echo 3 | sudo tee /proc/sys/vm/drop_caches; sudo fstrim -av"
bpf_basic_command = "sudo python3 {} {} {}"

output_filename = "{}/wiredtiger_limit-{}_pcsize-{}_readratio-{}.{}"


memory_limit = 10
cache_size = 500000
read_ratios = [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1]

for read_ratio in read_ratios:
    wiredtiger_output_filename = output_filename.format(result_dir, memory_limit / 10, cache_size, read_ratio, "wtout")
    wiredtiger_command = wiredtiger_basic_command.format(memory_limit, target, cache_size, read_ratio, wiredtiger_output_filename)
    bpf_output_filename = output_filename.format(result_dir, memory_limit / 10, cache_size, read_ratio, "bpfout")
    bpf_trace_output_filename = output_filename.format(result_dir, memory_limit / 10, cache_size, read_ratio, "trace")
    bpf_command = bpf_basic_command.format(bpf, bpf_trace_output_filename, bpf_output_filename)

    print(wiredtiger_command)
    print(bpf_command)
    # time.sleep(1)
    # bpf_process = subprocess.Popen(bpf_command, shell=True)
    # time.sleep(5)
    subprocess.run(wiredtiger_command, shell=True)
    # kill_command = "sudo kill -2 {}".format(bpf_process.pid + 2)
    # subprocess.run(kill_command, shell=True)
    # time.sleep(5)
