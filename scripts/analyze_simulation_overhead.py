import sys


sampling_length = 25
step_ops = 10000


sampling_file_base = "{}/adapter2_changed.latency"
nosampling_file_base = "{}/adapter_nosampling_changed.latency"
multighost_file_base = "{}/adapter2_multighost_changed.latency"
baseline_file_base = "{}/baseline_changed.latency"


sampling_file = sampling_file_base.format(sys.argv[1])
nosampling_file = nosampling_file_base.format(sys.argv[1])
multighost_file = multighost_file_base.format(sys.argv[1])
baseline_file = baseline_file_base.format(sys.argv[1])


for latency_file in [baseline_file, sampling_file, nosampling_file, multighost_file]:
    lines = open(latency_file, "r").readlines()
    for index, line in enumerate(lines):
        split = line.split()
        if split[1] == "Done" and int(split[0]) > 10000000:
            latency = 0
            convergence = 0
            for i in range(index - sampling_length, index, 1):
                latency += int(lines[i].split()[1])
            print(latency / step_ops / sampling_length)

            i = index - 1
            while lines[i].split()[1] != "Simulation":
                convergence += int(lines[i].split()[1])
                i -= 1
            print(convergence)

        if index == len(lines) - 1:
            latency = 0
            for i in range(index - sampling_length, index, 1):
                latency += int(lines[i].split()[1])
            print(latency / step_ops / sampling_length)
