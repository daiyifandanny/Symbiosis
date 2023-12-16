#! /usr/bin/env python3
import pandas as pd
import sys


def get_memory_capacity_gb():
    return 1


class RowObject(object):

    def __init__(self, memory_ratio, compress_ratio, miss_cost, load_dist):
        print('-----')
        self.memory_ratio = memory_ratio
        self.compress_ratio = compress_ratio
        self.miss_cost = miss_cost
        self.load_dist = load_dist
        self.pc_size_lat_dict = {}
        self.min_lat = 1000000000000000
        self.min_lat_pc_size = None
        self.min_lat_pc_size_gb = None
        self.zero_ac_lat = None
        self.zero_pc_lat = None
        self.MEM_CAPACITY = get_memory_capacity_gb()
        self.zero_ac_lat_to_min_lat_ratio = None
        self.zero_pc_lat_to_min_lat_ratio = None

    @staticmethod
    def get_row_column_name_list():
        row_col_name_list = [
            'memory_ratio', 'compress_ratio', 'miss_cost', 'load_dist', \
                'min_lat_pc_size', 'min_lat_pc_size_gb', 'min_lat', \
            'zero_ac_lat', 'zero_pc_lat', \
                'zero_ac_lat_to_min_lat', 'zero_pc_lat_to_min_lat',
        ]
        return row_col_name_list

    def get_case_name(self):
        return 'memory_ratio:{} compress_ratio:{} miss_cost:{} load:{}'.\
            format(self.memory_ratio, self.compress_ratio, self.miss_cost, self.load_dist)

    def to_row_list(self):
        if self.zero_ac_lat is None:
            print('{}'.format(self.get_case_name()))
            raise RuntimeError('zero_ac_lat is None')
        if self.zero_pc_lat is None:
            print('{}'.format(self.get_case_name()))
            raise RuntimeError('zero_pc_lat is None')
        self.zero_ac_lat_to_min_lat_ratio = self.zero_ac_lat / self.min_lat
        self.zero_pc_lat_to_min_lat_ratio = self.zero_pc_lat / self.min_lat
        return [
            self.memory_ratio, self.compress_ratio, self.miss_cost, self.load_dist,\
                self.min_lat_pc_size, self.min_lat_pc_size_gb, self.min_lat, \
                self.zero_ac_lat, self.zero_pc_lat, \
                self.zero_ac_lat_to_min_lat_ratio, self.zero_pc_lat_to_min_lat_ratio,
        ]

    def add_exp_item(self, pc_size, total_latency):
        print(f'add pc:{pc_size} total_latency:{total_latency}')
        if (pc_size - 0) < 0.0000001:
            self.zero_pc_lat = total_latency
        if pc_size == self.memory_ratio:
            self.zero_ac_lat = total_latency
        if total_latency < self.min_lat:
            self.min_lat = total_latency
            self.min_lat_pc_size = pc_size
            self.min_lat_pc_size_gb = round(
                (self.MEM_CAPACITY / self.compress_ratio) * pc_size, 4)


def raw_result_df_add_info(df):
    MEM_CAPACITY = get_memory_capacity_gb()
    df['uncompressed_data_size'] = MEM_CAPACITY / df['memory_ratio']
    ROUND_NUM = 5
    df['pc_size_gb'] = round(df['uncompressed_data_size'] * df['pc_size'],
                             ROUND_NUM)
    df['ac_size_gb'] = MEM_CAPACITY - round(df['pc_size_gb'], ROUND_NUM)


def process_perf_gain_data(csv_name):
    output_csv_name = csv_name.replace('.csv', '_perf_gain.csv')
    df = pd.read_csv(csv_name)

    memory_ratio_list = df['memory_ratio'].unique()
    compress_ratio_list = df['compress_ratio'].unique()
    # miss_cost_list = df['miss_cost'].unique()
    miss_cost_list = [10, 50, 100]
    load_dist_list = [0, 1]
    row_list = []
    for memory_ratio in memory_ratio_list:
        for compress_ratio in compress_ratio_list:
            for miss_cost in miss_cost_list:
                for load_dist in load_dist_list:
                    cur_row_obj = RowObject(memory_ratio, compress_ratio,
                                            miss_cost, load_dist)
                    cur_df = df.loc[df['memory_ratio'] == memory_ratio]
                    cur_df = cur_df.loc[cur_df['compress_ratio'] ==
                                        compress_ratio]
                    cur_df = cur_df.loc[cur_df['miss_cost'] == miss_cost]
                    cur_df = cur_df.loc[cur_df['load_dist'] == load_dist]
                    for idx, row in cur_df.iterrows():
                        cur_row_obj.add_exp_item(row['pc_size'],
                                                 row['total_latency'])
                    row_list.append(cur_row_obj.to_row_list())
    out_df = pd.DataFrame(row_list,
                          columns=RowObject.get_row_column_name_list())
    out_df['d_u'] = round(1 / out_df['memory_ratio'], 4)
    out_df['d_c'] = round(out_df['d_u'] * out_df['compress_ratio'], 4)
    out_df.to_csv(output_csv_name, index=False)


def print_usage(argv0):
    print(f'{argv0} <csv_name>')


if __name__ == '__main__':
    if len(sys.argv) != 2:
        print_usage(sys.argv[0])
        sys.exit(1)
    csv_name = sys.argv[1]
    process_perf_gain_data(csv_name)
