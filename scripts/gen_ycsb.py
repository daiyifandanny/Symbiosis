#!/usr/bin/env python3
import argparse
import itertools
import subprocess
import os
import sys


ycsb_folder = sys.argv[1]
workload_folder = sys.argv[2]
output_folder = sys.argv[3]


def prepare_files(workloads):
    for w in workloads:
        for s in [0.2, 0.4, 0.6, 0.8, 1]:
            base_size = 100000000
            file = f"temp/{w}-{s}.ycsb"
            if True or not os.path.exists(file):
                subprocess.run(
                    f"{ycsb_folder}/bin/ycsb.sh run basic "
                    f"-P {workload_folder}/{w}{'90' if (w[0] != 'h') else ''}_10M_{s} "
                    f"-p fieldcount=1 -p fieldlength=0 "
                    f"-p recordcount={int(base_size/s)} -p operationcount={base_size} > {file}", shell=True)
        
            outfile = open(f"{output_folder}/{w}_100M_{s}.out.req.trace", "w")
            infile = open(file, "r")
            for line in infile.readlines():
                split = line.split()
                if len(split) > 3 and split[1] == "usertable":
                    op = 0 if split[0] == "READ" else 1
                    assert(op == 0)
                    value = int(split[2][4:])
                    print(f"{value}", file=outfile)


if __name__ == "__main__":
    workloads = ["uniform", "zipfian", "hotspot70", "hotspot80"]
    # workloads = ["hotspot90"]
    prepare_files(workloads)
