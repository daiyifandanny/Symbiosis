#! /usr/bin/env python3

import sys


def print_usage(argv0):
    print(f'{argv0} <trace>')


if len(sys.argv) != 2:
    print_usage(sys.argv[0])
    sys.exit(1)

min_key = 10000000000
max_key = 0
with open(sys.argv[1]) as f:
    for line in f:
        cur_key = int(line)
        if cur_key > max_key:
            max_key = cur_key
        if cur_key < min_key:
            min_key = cur_key

print(f'min:{min_key} max_key:{max_key}')
