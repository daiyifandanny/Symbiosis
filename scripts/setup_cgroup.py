import subprocess


names = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 100]
mbs = [int(1024 * x / 10) + 5 for x in names]

for item in names:
    subprocess.run("sudo cgcreate -g memory:{}".format(item), shell=True)

subprocess.run("sudo chown -R yifan /sys/fs/cgroup/memory", shell=True)

for name, mb in zip(names, mbs):
    subprocess.run("echo {}m > /sys/fs/cgroup/memory/{}/memory.limit_in_bytes".format(mb, name), shell=True)

subprocess.run("sudo swapoff -a", shell=True)
subprocess.run("echo off | sudo tee /sys/devices/system/cpu/smt/control", shell=True)

for x in range(0, 40, 1):
    subprocess.run("echo \"2900000\" | sudo tee /sys/devices/system/cpu/cpu{}/cpufreq/scaling_max_freq".format(x), shell=True)
