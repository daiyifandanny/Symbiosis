#! /usr/bin/env python3

import sys
import os
import pandas as pd
"""
Process the output of the cache simulation
"""

import simulator_case_common as sim_case
import batch_run_sim_expr as sim_batch


class SimBatch(object):

    def __init__(self, result_dir: str):
        self.result_dir = result_dir
        self.case_list = []
        self.row_list = []
        self._setup_variables()
        self.df: pd.DataFrame = None

    def _setup_variables(self):
        self.ROW_STR_LIST = [
            'memory_ratio', 'pc_size', 'compress_ratio', 'miss_cost',
            'load_dist', 'total_latency'
        ]

    def save_df_to_csv(self):
        if self.df is None:
            print('Cannot save df to csv')
            return
        self.df.to_csv(f'{self.result_dir}/results_all.csv', index=False)

    def load_results(self):
        for fname in os.listdir(self.result_dir):
            if not fname.startswith('memory_ratio'):
                continue
            cur_case = sim_case.load_output_to_case_obj(self.result_dir, fname)
            self.case_list.append(cur_case)
            self.row_list.append(self.gen_case_row(cur_case))
        print(f'Load {len(self.case_list)} cases in total.')
        self.df = pd.DataFrame(self.row_list, columns=self.row_str_list())
        self.df = self.df.sort_values(by=[
            'memory_ratio', 'compress_ratio', 'miss_cost', \
                'pc_size', 'load_dist'], \
                    ignore_index=True)
        print(self.df)
        self.save_df_to_csv()

    def row_str_list(self):
        return self.ROW_STR_LIST

    def gen_case_row(self, case: sim_case.CacheExpCase):
        assert case.pc_size is not None
        return [
            case.memory_ratio, case.pc_size, case.compress_ratio,
            case.miss_cost, case.load_dist,
            case.get_total_latency()
        ]


def print_usage(argv0):
    print(f'Usage {argv0} <result_dir>')


def process_result_dir(result_dir: str):
    sim_batch = SimBatch(result_dir)
    sim_batch.load_results()


if __name__ == '__main__':
    if len(sys.argv) != 2:
        print_usage(sys.argv[0])
        sys.exit(1)
    result_dir = sys.argv[1]
    process_result_dir(result_dir)
