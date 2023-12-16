#! /usr/bin/env python3

import sys
import os
"""
Usage:
# Get the ycsb output (input of this script)
$YCSB_HOME/bin/ycsb run basic -P workloads/workloadc-fast23 > workloadc-fast23.output
"""


def get_disk_byte(disk_size_str: str) -> int:
    disk_size_str = disk_size_str.lower()
    mapper = {
        'k': 1024,
        'm': 1024 * 1024,
        'g': 1024 * 1024 * 1024,
    }
    sz_str = disk_size_str[:-1]
    sz_byte = int(sz_str) * mapper[disk_size_str[-1]]
    assert sz_byte % 4096 == 0
    return sz_byte


def calc_val_size(num_total_key: int, disk_byte: int) -> int:
    return int(disk_byte / num_total_key)


def key_seq_to_block_no(req_key_seq_no: int, val_size_byte: int) -> int:
    return int((req_key_seq_no * val_size_byte) / 4096)


def ycsb_output_invalid_line(line: str) -> bool:
    if "SCAN usertable" in line:
        return False
    if "READ usertable" not in line:
        return True
    return False


def dump_split_scan_read() -> bool:
    return True


def extract_ycsb_line_key_numonly(line: str, is_scan=False) -> str:
    items = line.split()
    key_item = items[2]
    assert key_item.startswith('user')
    key_item = key_item[4:]
    assert key_item.isnumeric()
    if is_scan:
        start_key = int(key_item)
        num_key = int(items[3])
        key_list = [(start_key + i) for i in range(num_key)]
        return key_list
    else:
        return int(key_item)


def from_req_trace_to_block_trace(req_trace_name: str, block_trace_name: str,
                                  num_unique_key: int, disk_data_byte: int):
    val_size_byte = calc_val_size(num_unique_key, disk_data_byte)
    print(f'Value size: {val_size_byte}(B)')
    if val_size_byte > 4096:
        print(
            f'Warning: value size must be larger than 4K to reach the disk_data_byte ({disk_data_byte})'
        )
    blk_no_set = set()
    with open(req_trace_name) as fr_req:
        with open(block_trace_name, 'w') as fw_blk:
            for line in fr_req:
                req_seq = int(line)
                cur_bno = key_seq_to_block_no(req_seq, val_size_byte)
                blk_no_set.add(cur_bno)
                fw_blk.write(f'{cur_bno}\n')
    print(
        f'Number of unique blocks:{len(blk_no_set)} (size mb:{len(blk_no_set)*4/1024})'
    )


def gen_trace(basic_output_name: str, num_unique_key: int, disk_data_byte: int,
              gen_block_trace: bool) -> None:
    req_trace_name = f'{basic_output_name}.req.trace'
    block_trace_name = f'{basic_output_name}.block.trace'
    key_set = {}
    num_accessed_uniq_key = 0
    min_key = 1000000000
    max_key = 0

    scan_sep_trace_name = req_trace_name.replace('.req.trace',
                                                 '.scan.req.trace')
    get_sep_trace_name = req_trace_name.replace('.req.trace', '.get.req.trace')
    sep_scan_trace_f = None
    sep_get_trace_f = None
    if dump_split_scan_read():
        sep_get_trace_f = open(get_sep_trace_name, 'w')

    with open(basic_output_name) as fr:
        with open(req_trace_name, 'w') as fw_req:

            def bookkeep_one_key(key_item):
                nonlocal min_key
                nonlocal max_key
                nonlocal key_set
                nonlocal num_accessed_uniq_key
                if key_item > max_key:
                    max_key = key_item
                if key_item < min_key:
                    min_key = key_item
                if key_item not in key_set:
                    key_set[key_item] = num_accessed_uniq_key
                    num_accessed_uniq_key += 1

            for line in fr:
                line = line.strip()
                if ycsb_output_invalid_line(line):
                    continue
                if 'SCAN' in line:
                    if sep_scan_trace_f is None and dump_split_scan_read():
                        sep_scan_trace_f = open(scan_sep_trace_name, 'w')
                    key_list = extract_ycsb_line_key_numonly(line, is_scan=True)
                    for key_item in key_list:
                        bookkeep_one_key(key_item)
                        fw_req.write(f'{key_item}\n')
                        if dump_split_scan_read():
                            sep_scan_trace_f.write(f'{key_item}\n')
                elif 'READ' in line:
                    key_item = extract_ycsb_line_key_numonly(line)
                    if dump_split_scan_read():
                        sep_get_trace_f.write(f'{key_item}\n')
                    bookkeep_one_key(key_item)
                    assert key_item in key_set
                    fw_req.write(f'{key_item}\n')
    print('Done for request trace')
    print(f'Number of unique keys (from input):{num_unique_key}')
    print(f'Number of accessed unique keys: {num_accessed_uniq_key}')
    print(f'    min_key:{min_key} max_key:{max_key}')
    if dump_split_scan_read() and sep_scan_trace_f is None:
        sep_get_trace_f.close()
        os.remove(get_sep_trace_name)
    #assert max_key >= num_unique_key
    if gen_block_trace:
        # Block trace
        from_req_trace_to_block_trace(req_trace_name, block_trace_name,
                                      num_unique_key, disk_data_byte)


if __name__ == '__main__':
    if len(sys.argv) != 5:
        print(
            f'Usage {sys.argv[0]} <Basic workload output name> <num_uniq_key> <disk_data_size> <0|1>(gen_block_trace)'
        )
        sys.exit(1)
    num_unique_key = int(sys.argv[2])
    disk_data_byte = get_disk_byte(sys.argv[3])
    gen_trace(sys.argv[1], num_unique_key, disk_data_byte,
              int(sys.argv[4]) == 1)
