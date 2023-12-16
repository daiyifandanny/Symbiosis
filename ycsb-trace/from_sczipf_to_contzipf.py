#! /usr/bin/env python

import sys
import math
from typing import List
import gen_req_trace as gtrace
from collections import deque
"""
Generate continuous zipf distribution from scattered zipf req trace
"""


def gen_contzipf_trace(sc_req_trace_name: str, num_unique_key: int,
                       disk_data_byte: int, gen_block_trace: bool,
                       pct_list: List[float]) -> None:
    assert len(pct_list) > 1
    assert sum(pct_list) == 1.0
    key_mapping_dict = {}
    slot_key_range_list = [0]
    slot_key_set = {idx: dict() for idx in range(len(pct_list))}
    slot_key_stack = {idx: deque() for idx in range(len(pct_list))}
    for idx in range(len(pct_list)):
        slot_key_range_list.append(
            math.ceil(num_unique_key * pct_list[idx]) +
            slot_key_range_list[idx - 1])
    print(f'slot_key_range_list:{slot_key_range_list}')

    def get_key_slot(key: int):
        agg_prev = 0
        for idx in range(len(pct_list)):
            # print(f'id:{idx} agg_prev:{agg_prev} upper:{agg_prev + slot_key_range_list[idx + 1]}')
            if agg_prev <= key <= agg_prev + slot_key_range_list[idx + 1]:
                return idx
            agg_prev += slot_key_range_list[idx + 1]
        assert False

    req_trace_name = sc_req_trace_name.replace('Job_sczipf', 'Job_contzipf')
    block_trace_name = req_trace_name.replace('req.trace', 'block.trace')
    with open(sc_req_trace_name) as f:
        key_freq_dict = {}
        num_req = 0
        for line in f:
            line = line.strip()
            key = int(line)
            cur_key_new_slot = get_key_slot(key)
            assert cur_key_new_slot in slot_key_set
            if key not in slot_key_set[cur_key_new_slot]:
                slot_key_set[cur_key_new_slot][key] = 0
                slot_key_stack[cur_key_new_slot].append(key)
            if key not in key_freq_dict:
                key_freq_dict[key] = 0
            key_freq_dict[key] += 1
            num_req += 1
        sorted_dict = dict(
            sorted(key_freq_dict.items(),
                   key=lambda item: item[1],
                   reverse=True))
        print(f'Total num_req:{num_req}')
        pre_freq = 10000000000
        # Verify the sorting, since the dict() preverse insert order is said to be
        # implementation dependent...
        for k, freq in sorted_dict.items():
            assert pre_freq >= freq
            # pick one key in the corresponding slot
            for slot_id in range(len(pct_list)):
                cur_slot_key_stack = slot_key_stack[slot_id]
                if bool(cur_slot_key_stack):
                    # cur_new_key = random.choice(tuple(cur_slot_key_set))
                    cur_new_key = cur_slot_key_stack.popleft()
                    key_mapping_dict[k] = cur_new_key
                    if len(key_mapping_dict) % 1000 == 0:
                        print(
                            f'size of key_mapping:{len(key_mapping_dict)} slot_key_set_num:{len(cur_slot_key_stack)}'
                        )
                    if not bool(cur_slot_key_stack):
                        print(f'slot:{slot_id} becomes empty')
                    break
            pre_freq = freq
    with open(sc_req_trace_name) as fr:
        with open(req_trace_name, 'w') as f_req:
            for line in fr:
                line = line.strip()
                key = int(line)
                assert key in key_mapping_dict
                f_req.write(f'{key_mapping_dict[key]}\n')
    if gen_block_trace:
        gtrace.from_req_trace_to_block_trace(req_trace_name, block_trace_name,
                                             num_unique_key, disk_data_byte)


def get_pct_list(pct_str: str):
    items = pct_str.split(',')
    return [float(item) for item in items]


if __name__ == '__main__':
    if len(sys.argv) != 6:
        print(
            f'Usage {sys.argv[0]} <sc_req_trace> <num_uniq_key> <disk_data_size> <0|1>(gen_block_cache) <pct_list>(sep by comma)'
        )
        sys.exit(1)
    num_unique_key = int(sys.argv[2])
    disk_data_byte = gtrace.get_disk_byte(sys.argv[3])
    gen_contzipf_trace(sys.argv[1], num_unique_key, disk_data_byte,
                       int(sys.argv[4]) == 1, get_pct_list(sys.argv[5]))
