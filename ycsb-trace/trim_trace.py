#! /usr/bin/env python3
"""
For a trace to have a given number of line
"""

import sys


def print_usage(argv0):
    print(f'{argv0} <trace> <num_line> <max_key>')


if len(sys.argv) != 4:
    print_usage(sys.argv[0])
    sys.exit(1)

input_name = sys.argv[1]
num_line = int(sys.argv[2])
max_key = int(sys.argv[3])
output_name = input_name.replace('out.req.trace', 'out.trim.req.trace')
with open(output_name, 'w') as fw:
    with open(input_name) as fr:
        nl = 0
        result_nl = 0
        for line in fr:
            cur_key = int(line)
            if cur_key >= max_key:
                print(f'    skip key:{cur_key}')
                nl += 1
                continue
            if result_nl < num_line:
                result_nl += 1
                fw.write(line)
            nl += 1
        print(f'trim from:{nl-1} to:{num_line} (target) actual:{result_nl}')
        assert result_nl == num_line
