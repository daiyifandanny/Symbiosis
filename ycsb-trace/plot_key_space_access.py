#! /usr/bin/env python3

import sys
from typing import Dict
import numpy as np
import pandas as pd

from bokeh.layouts import gridplot
from bokeh.models import Legend, FuncTickFormatter, NumeralTickFormatter, SingleIntervalTicker, LinearAxis, FixedTicker
from bokeh.plotting import figure, output_file, show
from bokeh.io import export_png

# sudo apt-get -y install chromium-browser chromium-chromedriver firefox-geckodriver
'''
# some useful examples for later reference
p.xaxis.ticker=FixedTicker(ticks=[3, 9])
p.xaxis.formatter = FuncTickFormatter(code="""
    var mapping = {3: "$20 000", 9: "$50 000"};
        return mapping[tick];
        """)""")
'''


def plot_key_range_hotness(access_freq_dict: Dict[int, int], num_bar: int,
                           png_name: str):
    key_list = sorted(access_freq_dict.keys())
    # for k in key_list:
    # print(f'k:{k} freq:{access_freq_dict[k]}')
    bar_num_key = round(len(key_list) / num_bar)
    key_list_idx = 0
    xs = []
    ys = []
    while key_list_idx < len(key_list):
        start_key = str(key_list[key_list_idx])
        xs.append(str(key_list[key_list_idx]))
        cur_bar_num = 0
        for i in range(bar_num_key):
            cur_bar_num += access_freq_dict[key_list[key_list_idx]]
            key_list_idx += 1
            if key_list_idx == len(key_list):
                break
        ys.append(cur_bar_num)

    p = figure(x_range=xs,
               plot_width=1000,
               plot_height=500,
               title="Key Range Access Number",
               toolbar_location=None,
               tools="")

    p.vbar(x=xs, top=ys, width=0.1)
    p.xgrid.grid_line_color = None
    p.yaxis.formatter = NumeralTickFormatter(format="0a")
    NUM_TICK = 10
    num_sorted_key = len(key_list)
    interval = int(num_sorted_key / NUM_TICK) + 1
    interval = int(10000 * int(interval / 10000))
    if interval == 0:
        interval = 1
    ticker_list = []
    for i in range(0, num_sorted_key - 1, interval):
        ticker_list.append(key_list[i])
    print(ticker_list)
    #p.xaxis.ticker = FixedTicker(ticks=ticker_list)
    #p.x_range.start = 0
    p.xaxis.ticker = ticker_list
    p.xaxis.formatter = NumeralTickFormatter(format="0,0")
    #print(ticker_list)
    #p.xaxis.ticker = ticker_list
    # p.axis.major_tick_line_color = None
    p.y_range.start = 0
    #p.xaxis.major_label_text_color = 'black'
    # p.xaxis.major_label_overrides = {}
    export_png(p, filename=png_name)


def analyze_key_space_locality(key_freq_dict: Dict[int, int], max_key: int):
    sorted_dict = dict(
        sorted(key_freq_dict.items(), key=lambda item: item[1], reverse=True))
    num_access = sum(sorted_dict.values())
    print(f'NumAccess:{num_access} max_key(input):{max_key}')
    freq_pct_dict = {k: v / num_access for k, v in sorted_dict.items()}
    # Only look at the frequency
    agg_num_access = 0
    uniq_key_id = 0
    for k, v in freq_pct_dict.items():
        agg_num_access += sorted_dict[k]
        print(
            f'{k} pdf:{v:.4f} cdf:{agg_num_access/num_access:.4f} uniq_kid:{uniq_key_id}'
        )
        uniq_key_id += 1
    # Sort it by key range and look at the frequency
    print('SORT key by space locality')
    agg_num_access = 0
    uniq_key_id = 0
    for k in sorted(key_freq_dict.keys()):
        agg_num_access += sorted_dict[k]
        print(
            f'{k} pdf:{freq_pct_dict[k]:.4f} cdf:{agg_num_access/num_access:.4f} uniq_kid:{uniq_key_id} key_space_pct:{k/max_key:.4f}'
        )
        uniq_key_id += 1


def print_usage(argv0):
    print(f'Usage {argv0} analyze|plot <trace_name> <num_bar|max_key>')


def main(trace_name: str, num_bar: int, do_analyze: bool):
    access_freq_dict = {}
    with open(trace_name) as f:
        for line in f:
            line = line.strip()
            cur_key = int(line)
            if cur_key not in access_freq_dict:
                access_freq_dict[cur_key] = 0
            access_freq_dict[cur_key] += 1
    png_name = f'{trace_name}.key_range_access.png'
    if do_analyze:
        analyze_key_space_locality(access_freq_dict, num_bar)
    else:
        plot_key_range_hotness(access_freq_dict, num_bar, png_name)


if __name__ == '__main__':
    if len(sys.argv) != 4:
        print_usage(sys.argv[0])
        sys.exit(1)
    do_analyze = sys.argv[1] == 'analyze'
    if sys.argv[1] == 'analyze':
        do_analyze = True
    elif sys.argv[1] == 'plot':
        do_analyze = False
    else:
        print_usage(sys.argv[0])
        sys.exit(1)
    trace_name = sys.argv[2]
    num_bar = int(sys.argv[3])
    if do_analyze:
        main(trace_name, int(sys.argv[3]), do_analyze)
    else:
        main(trace_name, num_bar, do_analyze)
