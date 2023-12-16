#! /usr/bin/env python3

import sys
import ast
import os

CACHESTAT_ROOT_DIR = os.getenv("CACHESTAT_ROOT_DIR")
if CACHESTAT_ROOT_DIR is None:
    print(
        'CACHESTAT_ROOT_DIR environment variable does not exist. Please source or relogin'
    )
    print('Remember to run the setup_cache_sim.sh though')
    sys.exit(1)


class CacheExpCase(object):

    def __init__(self, arg1, arg2, arg3, arg4):
        """
        Corresponds to the run_simulator_general2.py's arg list
        """
        self.memory_ratio = arg1
        self.compress_ratio = arg2
        self.miss_cost = arg3
        self.load_dist = arg4
        self.pc_size = None
        self.stats_dict = None
        self.input_trace_name = None
        self.OUTPUT_NAME_BASE = "memory_ratio-{}_pcsize-{}_appmisscost-{}_ratio-{}_distribution-{}.txt"

    def set_input_trace_name(self, input_trace_name: str):
        print('input_trace_name set to: {}'.format(input_trace_name))
        self.input_trace_name = input_trace_name

    def set_pc_size(self, sz):
        self.pc_size = sz

    def get_total_latency(self):
        return self.stats_dict['total_latency']

    def gen_cmd(self):
        script_fullpath = f'{CACHESTAT_ROOT_DIR}/scripts/run_simulator_general2.py'
        cmd_base = f'python3 {script_fullpath}'
        cmd = f'{cmd_base} {self.memory_ratio} {self.compress_ratio} {self.miss_cost} {self.load_dist}'
        if self.input_trace_name is not None:
            cmd += f' trace:{self.input_trace_name}'
        return cmd

    def gen_case_summary(self) -> str:
        SUMMARY_BASE = "mem-ratio:{} compress_ratio:{} miss_cost:{} load_dist:{}"
        return SUMMARY_BASE.format(self.memory_ratio, self.compress_ratio,
                                   self.miss_cost, self.load_dist)

    def get_stats_output_name(self) -> str:
        """
        Only the leaf filename.
        """
        assert self.pc_size is not None
        return self.OUTPUT_NAME_BASE.format(self.memory_ratio, self.pc_size,
                                            self.miss_cost, self.compress_ratio,
                                            self.load_dist)

    def load_stats_output(self, result_dir: str) -> None:
        output_stats_path = f'{result_dir}/{self.get_stats_output_name()}'
        with open(output_stats_path) as f:
            data = f.read()
            self.stats_dict = ast.literal_eval(data)

    @staticmethod
    def get_min_est_hour():
        return 1

    @staticmethod
    def get_max_est_hour():
        return 2


def load_output_to_case_obj(result_dir: str, fname: str) -> CacheExpCase:
    case_str = fname.replace('.txt', '')
    case_str = case_str.replace('memory_ratio', 'mmemratio')
    print(case_str)
    items = case_str.split('_')

    def get_item_val(item_str: str, tp: type):
        cur_item = tp((item_str.split('-'))[1])
        return cur_item

    mem_ratio = get_item_val(items[0], float)
    pc_size = get_item_val(items[1], float)
    miss_cost = get_item_val(items[2], int)
    compress_ratio = get_item_val(items[3], float)
    load_dist = get_item_val(items[4], int)
    cur_case = CacheExpCase(mem_ratio, compress_ratio, miss_cost, load_dist)
    cur_case.set_pc_size(pc_size)
    cur_case.load_stats_output(result_dir)
    return cur_case
