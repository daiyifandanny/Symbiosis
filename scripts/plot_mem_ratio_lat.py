#! /usr/bin/env python3

import sys
import pandas as pd
from zplot import *
import numpy as np
"""
Plot the influence of memory ratio (varies the DataSize)
"""


def get_mem_capacity_gb():
    return 1


def do_remove_tmp_file():
    return False


def plot_mem_ratio_lat(csv_name, compress_ratio, miss_cost, load_dist, x_name):
    # Preprocessing the data
    df = pd.read_csv(csv_name)
    df = df.loc[df['compress_ratio'] == compress_ratio]
    df = df.loc[df['miss_cost'] == miss_cost]
    df = df.loc[df['load_dist'] == load_dist]
    plot_memory_ratio_list = [
        round(x, 4) for x in list(np.arange(0.1, 1.01, 0.05))
    ]
    # plot_memory_ratio_list = [round(x, 4) for x in list(np.arange(0.1, 1.01, 0.1))]
    # plot_memory_ratio_list = [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]
    print(plot_memory_ratio_list)
    MEM_CAPACITY = get_mem_capacity_gb()
    df['uncompressed_data_size'] = MEM_CAPACITY / df['memory_ratio']
    ROUND_NUM = 5
    df['pc_size_gb'] = round(df['uncompressed_data_size'] * df['pc_size'],
                             ROUND_NUM)
    df['ac_size_gb'] = MEM_CAPACITY - round(df['pc_size_gb'], ROUND_NUM)
    print(df)
    # Do the plotting here
    ctype = 'eps'
    cur_title_name = 'mem_ratio_lat_compress-{}_misscost-{}_loaddist-{}_xname-{}'.\
        format(compress_ratio, miss_cost, load_dist, x_name)
    c = canvas(ctype, title=cur_title_name, dimensions=['2.8in', '1.9in'])
    p = plotter()
    M_1 = int(1000 * 1000)
    M_100 = int(M_1 * 100)
    Y_NAME = 'total_latency'
    if df[Y_NAME].max() > (M_100) * 9:
        y_max_val = int(M_100 * 10)
        ylabel_list = [['0', 0], ['250', int(M_100 * 2.5)],
                       ['500', int(M_100 * 5)], ['750', int(M_100 * 7.5)],
                       ['1K', int(M_100 * 10)]]
    else:
        y_max_val = int(M_100 * 8)
        ylabel_list = [['0', 0], ['200', int(M_100 * 2)],
                       ['400', int(M_100 * 4)], ['600', int(M_100 * 6)],
                       ['800', int(M_100 * 8)]]

    d = drawable(c,
                 xrange=[0, 1.0],
                 yrange=[0, y_max_val],
                 dimensions=['2.2in', '1.4in'],
                 coord=['0.5in', '0.4in'])
    grid(drawable=d,
         xrange=[0, 1.0],
         xstep=0.1,
         yrange=[0, y_max_val],
         ystep=y_max_val,
         linecolor='0.6,0.6,0.6',
         linedash=[2, 2])

    xtitle_str = 'Kernel Cache Size (GB)' if 'pc_size_gb' == x_name else 'App Cache Size (GB)'
    axis(d,
         xtitle=xtitle_str,
         xauto=[0, 1, 0.2],
         xtitleshift=[0, 3],
         ytitle='Total Latency (sec)',
         ymanual=ylabel_list)
    L = legend()
    line_color = '0.6,0.6,0.6'
    line_dash = '0'
    line_dash = [2, 2]
    marker_line_width = 0.5
    color_min = 0.15
    color_max = 0.7
    color_interval = round(
        (color_max - color_min) / (len(plot_memory_ratio_list) - 2), 4)
    cur_color = color_min
    color_str_dict = {}
    legend_dict = {mem_ratio: '' for mem_ratio in plot_memory_ratio_list}
    Y_NAME = 'total_latency'
    for idx, mem_ratio in enumerate(plot_memory_ratio_list):
        cur_color_str = f'{cur_color},{cur_color},{cur_color}'
        color_str_dict[float(mem_ratio)] = cur_color_str
        cur_color = round(cur_color + color_interval, 4)
        print(f'cur_color_val:{cur_color}')
        if idx == 0 or idx == (len(plot_memory_ratio_list) - 1):
            legend_dict[mem_ratio] = L

    for mem_ratio in reversed(plot_memory_ratio_list):
        print(mem_ratio)
        cur_df = df.loc[df['memory_ratio'] == mem_ratio]
        tmp_csv_name = f'tmp_{mem_ratio}.csv'
        cur_df.to_csv(tmp_csv_name, index=False)
        print(tmp_csv_name)
        cur_tb = table(tmp_csv_name)
        print(x_name)
        cur_color_str = color_str_dict[float(mem_ratio)]
        p.line(d,
               cur_tb,
               xfield=x_name,
               yfield=Y_NAME,
               linecolor=cur_color_str,
               linewidth=1.05,
               legend=legend_dict[mem_ratio],
               legendtext=f'D_u: {1/mem_ratio:.0f}G')
        print(f'mem_ratio:{mem_ratio:.2f}')
        p.points(d,
                 cur_tb,
                 xfield=x_name,
                 yfield=Y_NAME,
                 style='circle',
                 linecolor=cur_color_str,
                 linewidth=marker_line_width,
                 size=0.7,
                 fill=True,
                 fillcolor=cur_color_str)
        # Global minima
        min_lat = cur_df['total_latency'].min()
        min_lat_df = cur_df.loc[cur_df['total_latency'] == min_lat]
        tmp_min_csv_name = f'tmp_min_{mem_ratio}.csv'
        min_lat_df.to_csv(tmp_min_csv_name, index=False)
        if do_remove_tmp_file():
            os.remove(tmp_csv_name)

    # Put the global minima on the top
    for mem_ratio in plot_memory_ratio_list:
        tmp_min_csv_name = f'tmp_min_{mem_ratio}.csv'
        min_tb = table(tmp_min_csv_name)
        cur_color_str = color_str_dict[float(mem_ratio)]
        p.points(d,
                 min_tb,
                 xfield=x_name,
                 yfield='total_latency',
                 style='triangle',
                 size=1.6,
                 linewidth=0.5,
                 linecolor='black',
                 fill=True,
                 fillcolor=cur_color_str)
        if do_remove_tmp_file():
            os.remove(tmp_min_csv_name)

    L.draw(c,
           coord=[d.right() - 50, d.bottom() + 15],
           width=20,
           height=6,
           fontsize=7,
           hspace=-3,
           order=[1, 0])
    c.render()


def print_usage(argv0):
    print(
        f'{argv0} <csv> <compress_ratio> <miss_cost> <load_dist><0(uni)|1> <x-name>(k|a)'
    )


if __name__ == '__main__':
    if len(sys.argv) != 6:
        print_usage(sys.argv[0])
        sys.exit(1)
    csv_name = sys.argv[1]
    compress_ratio = float(sys.argv[2])
    miss_cost = int(sys.argv[3])
    load_dist = int(sys.argv[4])
    if sys.argv[5] == 'k':
        x_name = 'pc_size_gb'
    elif sys.argv[5] == 'a':
        x_name = 'ac_size_gb'
    else:
        print_usage(sys.argv[0])
        sys.exit(1)
    plot_mem_ratio_lat(csv_name, compress_ratio, miss_cost, load_dist, x_name)
