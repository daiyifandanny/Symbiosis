import pexpect
import subprocess
import time


working_dir = "/home/yifan/research/cache/bpf/cachestat/test"
# exe_cmd = "cgexec -g memory:test -- {}/linear 256 -1".format(working_dir)
exe_cmd = "cgexec -g memory:10 -- {}/simple_read -c".format(working_dir)
page_stat_cmd = "sudo page-types --raw -Cl -f /nvme/test/tsukushi.txt > {}/page_stat.txt".format(working_dir)
# trace_filename = "{}/trace2.txt".format(working_dir)
trace_filename = "{}/trace1.txt".format(working_dir)
max_page = 256


# subprocess.run("cgexec -g memory:test -- {}/linear 256 1; sync; echo 3 | sudo tee /proc/sys/vm/drop_caches; sudo fstrim -a -v".format(working_dir), shell=True)
exe = pexpect.spawn(exe_cmd)
with open(trace_filename, "r") as trace_file:
    lines = trace_file.readlines()
    current_line: int = 0
    while True:
        time.sleep(0.1)
        subprocess.run(page_stat_cmd, shell=True)
        target = lines[current_line].split()[0]
        print("next: {}".format(target))        
        step_num: int = int(input("step: "))
        for _ in range(0, step_num):
            target = lines[current_line].split()[0]
            # print(target)
            exe.sendline(target)
            current_line += 1
            current_line %= max_page
