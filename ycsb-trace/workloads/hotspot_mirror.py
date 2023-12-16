#! /usr/bin/env python3

import sys


def do_hotspot_mirror(input_trace: str, max_key: int):
    output_name = input_trace.replace('.trace', '.mirror.trace')
    print(output_name)
    with open(input_trace) as f:
        with open(output_name, 'w') as fw:
            for line in f:
                line = line.strip()
                key = int(line)
                new_key = int(max_key - key)
                assert new_key >= 0
                fw.write(f'{new_key}\n')


def print_usage(argv0):
    print(f'Usage: {argv0} <input_trace> <max_key>')


if __name__ == '__main__':
    if len(sys.argv) != 3:
        print_usage(sys.argv[0])
        sys.exit(1)
    input_trace = sys.argv[1]
    max_key = int(sys.argv[2])
    do_hotspot_mirror(input_trace, max_key)
