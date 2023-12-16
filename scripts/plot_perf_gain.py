#! /usr/bin/env python3
import os
import sys
from zplot import *
from typing import List
import pandas as pd
"""
current cmd in use:
    python plot_perf_gain.py size ./results_SET1_SET2_perf_gain.csv 0.1,0.3,0.5,0.7,0.9
    python plot_perf_gain.py gain ./results_SET1_SET2_perf_gain.csv 0.1,0.3,0.5,0.7,0.9
"""


def do_remove_tmp_file():
    return True


def get_coord(num_horiz, num_vert, x, y):
    '''
    get the coord for each grid
    change the h_step, w_step for resize grid
    change col_sum, row_sum for more grid or less
    change base if only need more space under grids (like for text, legend)
    '''
    # x should start from 0
    # y should start from 0
    # base = [20, 20]
    base = [20, 20]
    axis_interval = 10
    #h_step = 70
    # w_step = 70  # this could be like a squire for each grid
    #h_step = 44
    h_step = 54
    w_step = 56
    col_sum = num_horiz
    row_sum = num_vert
    real_x = row_sum - x - 1
    real_y = y
    coord = [
        base[0] + real_y * (w_step + axis_interval), base[1] + real_x * (h_step)
    ]
    print('x:{} y:{}'.format(x, y))
    print(coord)
    return coord


def get_color_list(num_line, go_lighter=True):
    # 1 is lighter
    color_min = 0.15
    color_max = 0.7
    assert num_line > 2
    color_interval = round((color_max - color_min) / (num_line - 1), 4)
    cur_color = color_min
    color_str_list = []
    for idx in range(num_line):
        assert cur_color < 0.95
        cur_color_str = f'{cur_color},{cur_color},{cur_color}'
        color_str_list.append(cur_color_str)
        cur_color = round(cur_color + color_interval, 4)
    if not go_lighter:
        color_str_list.reverse()
    return color_str_list


def get_size_alpha_point_style(alpha_v, alpha_color):
    alpha_point_style_dict = {
        0.1: {
            'style': 'circle',
            'size': 1.2,
            'linewidth': 0.4,
        },
        0.2: {
            'style': 'diamond'
        },
        0.3: {
            'style': 'xline',
            'size': 1.2,
            'linewidth': 0.8,
        },
        0.4: {
            'style': 'square'
        },
        # 0.5: 'plusline',
        # 0.5: 'asterisk',
        # 0.5: {
        #     'style': 'star'
        # },
        0.5: {
            'style': 'diamond',
            'size': 1.3,
            'fill': True,
            'fillcolor': 'black',
            'linewidth': 0,
        },
        0.6: {
            'style': 'square'
        },
        0.7: {
            'style': 'vline',
            'size': 1.4,
            'linewidth': 1.2,
        },
        0.8: {
            'style': 'diamond'
        },
        0.9: {
            'style': 'square',
            'fill': True,
            'fillcolor': alpha_color,
            'linewidth': 0,
            'size': 1.4,
        },
        1.0: {
            'style': 'circle',
            'fill': True,
            'fillcolor': alpha_color,
            'linewidth': 0,
            'size': 1.4
        },
    }
    attr_dict = alpha_point_style_dict[alpha_v]
    attr_dict['linecolor'] = alpha_color
    return attr_dict


def plot_best_size(csv_name: str, alpha_list: List[float]):
    job_dist_list = [0, 1]
    miss_cost_list = [10, 50, 100]
    df = pd.read_csv(csv_name)

    ctype = 'eps'
    p = plotter()
    num_horiz = 6
    num_vert = 1
    c = canvas(ctype, title='sim_best_size', \
        dimensions=[num_horiz * 70 + 5, num_vert * 80 + 3])

    y_label_shift = [3, 0]
    x_label_shift = [0, 2]
    label_font_size = 5
    vertical_label_font_size = 7
    small_title_font_size = 6  # annotate method
    large_title_font_size = 7  # annotate Throughput , Resource Utilization
    # method_title_shift = [77, 0]
    title_font = 'Helvetica-Bold'
    method_title_font = 'Helvetica'

    # this values may need to tune for specific data
    title_shift = [0, -5]
    axis_line_width = 0.6
    tp_line_width = 1
    # line_width = 0.5
    tic_major_size = 2.0
    box_dim = [50, 50]

    def get_subplot_title(job_dist, miss_cost):
        job_str_dict = {0: 'U', 1: 'S'}
        return '{}(C_a={})'.format(job_str_dict[job_dist], miss_cost)

    def sort_alpha_list(l):
        sort_l = []
        delta = 0.5
        while delta >= 0:
            cur_v = round(0.5 - delta, 4)
            if cur_v in l:
                sort_l.append(cur_v)
            cur_v = round(0.5 + delta, 4)
            if cur_v in l and cur_v not in sort_l:
                sort_l.append(cur_v)
            delta = round(delta - 0.1, 4)
        return sort_l

    alpha_list = sort_alpha_list(alpha_list)
    print(alpha_list)

    color_str_list = get_color_list(len(alpha_list), go_lighter=False)
    print(f'color_list:{color_str_list}')
    alpha_color_str_dict = {
        a: color_str_list[idx] for idx, a in enumerate(alpha_list)
    }

    # memory_ratio_deny_list = [0.95, 0.9, 0.8, 0.85, 0.75, 0.7, 0.6, 0.55, 0.45]

    pic_idx = 0
    num_pic = int(num_vert * num_horiz)
    L = legend()
    pic_id_legend_dict = {i: '' for i in range(num_pic)}
    pic_id_legend_dict[num_pic - 1] = L
    pic_id_drawable_dict = {}
    pic_id_ytitle = {i: '' for i in range(num_pic)}
    pic_id_ytitle[0] = 'Optimal M_k (GB)'
    for job_dist in job_dist_list:
        for miss_cost in miss_cost_list:
            cur_coord = get_coord(num_horiz, num_vert, pic_idx // num_horiz,
                                  pic_idx % num_horiz)
            cur_d = drawable(canvas=c, xrange=[0, 1], yrange=[0, 1], \
                coord=cur_coord, dimensions=box_dim)
            pic_id_drawable_dict[pic_idx] = cur_d
            cur_title = get_subplot_title(job_dist, miss_cost)
            axis(drawable=cur_d, style='y', ylabelshift=y_label_shift, \
                ylabelfontsize=vertical_label_font_size, linewidth=axis_line_width,\
                    ticmajorsize=tic_major_size, yauto=[0, 1, 0.2],\
                    ytitle=pic_id_ytitle[pic_idx], ytitlesize=small_title_font_size)
            axis(drawable=cur_d, style='x', title=cur_title, \
                titlesize=large_title_font_size, titleshift=[0, -4],\
                    xauto=[0, 1, 0.2], dolabels=True, linewidth=axis_line_width, \
                        ticmajorsize=tic_major_size + 3, xlabelshift=[-2,-3],\
                            xlabelfontsize=vertical_label_font_size, xlabelrotate=90)
            # draw several lines
            cur_df = df.loc[df['load_dist'] == job_dist]
            cur_df = cur_df.loc[cur_df['miss_cost'] == miss_cost]
            for alpha in alpha_list:
                line_df = cur_df.loc[cur_df['compress_ratio'] == alpha]
                # line_df = line_df[~line_df.memory_ratio.isin(memory_ratio_deny_list)]
                cur_csv_name = 'tmp_perf_gain_{}_{}_{}.csv'.format(
                    miss_cost, alpha, job_dist)
                # print(line_df)
                # line_df = line_df.sort_values(by=['d_u'], ignore_index=True)
                line_df = line_df.sort_values(by=['memory_ratio'],
                                              ignore_index=True)
                line_df.to_csv(cur_csv_name, index=False)
                line_tb = table(cur_csv_name)
                # print(cur_tb.dump())
                # p.line(cur_d,
                #        line_tb,
                #        xfield='memory_ratio',
                #        yfield='min_lat_pc_size_gb',
                #         linecolor=alpha_color_str_dict[alpha],
                #        linedash=[2, 2],
                #        linewidth=0.5)

                cur_point_attr_dict = get_size_alpha_point_style(
                    alpha, alpha_color_str_dict[alpha])
                print(cur_point_attr_dict)
                p.points(cur_d,
                         line_tb,
                         xfield='memory_ratio',
                         yfield='min_lat_pc_size_gb',
                         legend=pic_id_legend_dict[pic_idx],
                         legendtext=f'alpha={alpha:.1f}',
                         **cur_point_attr_dict)
                if do_remove_tmp_file():
                    os.remove(cur_csv_name)
            # go to next pic
            pic_idx += 1
    last_d = pic_id_drawable_dict[num_pic - 1]
    print(f'last_d.right:{last_d.right()}')
    L.draw(c,
           coord=[last_d.right() - 8, last_d.bottom() + 30],
           width=3,
           height=3,
           fontsize=6,
           hspace=1,
           order=[0, 2, 4, 3, 1])
    # Let's do the xaxis label at one shot here
    c.text(coord=[last_d.right() + 13, last_d.bottom() - 3],
           text='M/D_u',
           size=7,
           rotate=0)
    c.render()


def get_gain_alpha_point_style(alpha_v, alpha_color):
    point_style_dict = {
        0.1: {
            'size': 1,
        },
        0.2: {
            'size': 1,
        },
        0.3: {
            'size': 1,
        },
        0.4: {
            'size': 0.9,
        },
        0.5: {
            'size': 0.8,
        },
        0.6: {
            'size': 0.7,
        },
        0.7: {
            'size': 0.6,
        },
        0.8: {
            'size': 0.6,
        },
        0.9: {
            'size': 0.6,
        },
        1.0: {
            'size': 0.6,
        }
    }
    attr_dict = point_style_dict[alpha_v]
    attr_dict['style'] = 'circle'
    attr_dict['linewidth'] = 0
    attr_dict['fill'] = True
    attr_dict['fillcolor'] = alpha_color
    return attr_dict


def get_gain_line_style(alpha_v):
    line_style_dict = {
        0.1: {
            'linewidth': 1.7,
        },
        0.2: {
            'linewidth': 1.5,
        },
        0.3: {
            'linewidth': 1.5,
        },
        0.4: {
            'linewidth': 1.3,
        },
        0.5: {
            'linewidth': 1.3,
        },
        0.6: {
            'linewidth': 1.0,
        },
        0.7: {
            'linewidth': 1,
        },
        0.8: {
            'linewidth': 0.8,
        },
        0.9: {
            'linewidth': 0.7,
        },
        1.0: {
            'linewidth': 0.7,
        }
    }
    attr_dict = line_style_dict[alpha_v]
    return attr_dict


def plot_perf_gain(csv_name: str, alpha_list: List[float]):
    # Keep the same is plot_best_size
    job_dist_list = [0, 1]
    miss_cost_list = [10, 50, 100]
    df = pd.read_csv(csv_name)

    ctype = 'eps'
    p = plotter()
    num_horiz = 6
    num_vert = 1
    c = canvas(ctype, title='sim_best_size_perf_gain', \
        dimensions=[num_horiz * 70 + 5, num_vert * 80 + 3])

    y_label_shift = [3, 0]
    x_label_shift = [0, 2]
    label_font_size = 5
    vertical_label_font_size = 7
    small_title_font_size = 6  # annotate method
    large_title_font_size = 7  # annotate Throughput , Resource Utilization
    # method_title_shift = [77, 0]
    title_font = 'Helvetica-Bold'
    method_title_font = 'Helvetica'

    # this values may need to tune for specific data
    title_shift = [0, -5]
    axis_line_width = 0.6
    tp_line_width = 1
    # line_width = 0.5
    tic_major_size = 2.0
    box_dim = [50, 50]

    def get_subplot_title(job_dist, miss_cost):
        job_str_dict = {0: 'U', 1: 'S'}
        return '{}(C_a={})'.format(job_str_dict[job_dist], miss_cost)

    ############################################################################
    # def sort_alpha_list(l):
    #     sort_l = []
    #     delta = 0.5
    #     while delta >= 0:
    #         cur_v = round(0.5 - delta, 4)
    #         if cur_v in l:
    #             sort_l.append(cur_v)
    #         cur_v = round(0.5 + delta, 4)
    #         if cur_v in l and cur_v not in sort_l:
    #             sort_l.append(cur_v)
    #         delta = round(delta - 0.1, 4)
    #     return sort_l
    # alpha_list = sort_alpha_list(alpha_list)
    # print(alpha_list)
    color_str_list = get_color_list(len(alpha_list), go_lighter=False)
    print(f'color_list:{color_str_list}')
    alpha_color_str_dict = {
        a: color_str_list[idx] for idx, a in enumerate(alpha_list)
    }
    pic_idx = 0
    num_pic = int(num_vert * num_horiz)
    L = legend()
    pic_id_legend_dict = {i: '' for i in range(num_pic)}
    pic_id_legend_dict[num_pic - 1] = L
    pic_id_drawable_dict = {}
    pic_id_ytitle = {i: '' for i in range(num_pic)}
    pic_id_ytitle[0] = 'Normalized Latency'
    for job_dist in job_dist_list:
        for miss_cost in miss_cost_list:
            cur_coord = get_coord(num_horiz, num_vert, pic_idx // num_horiz,
                                  pic_idx % num_horiz)
            cur_d = drawable(canvas=c, xrange=[0, 1], yrange=[1, 9], \
                coord=cur_coord, dimensions=box_dim, yscale='log3')
            # coord=cur_coord, dimensions=box_dim, yscale='linear')
            pic_id_drawable_dict[pic_idx] = cur_d
            cur_title = get_subplot_title(job_dist, miss_cost)
            y_manual_list = []
            for y_label_val in [1, 2, 3, 5, 9]:
                y_manual_list.append([str(y_label_val), y_label_val])
            axis(drawable=cur_d, style='y', ylabelshift=y_label_shift, \
                ylabelfontsize=vertical_label_font_size, linewidth=axis_line_width,\
                    ticmajorsize=tic_major_size, ymanual=y_manual_list,\
                    ytitle=pic_id_ytitle[pic_idx], ytitlesize=small_title_font_size)
            axis(drawable=cur_d, style='x', title=cur_title, \
                titlesize=large_title_font_size, titleshift=[0, -4],\
                    xauto=[0, 1, 0.2], dolabels=True, linewidth=axis_line_width, \
                        ticmajorsize=tic_major_size + 3, xlabelshift=[-2,-3],\
                            xlabelfontsize=vertical_label_font_size, xlabelrotate=90)
            # draw several lines
            cur_df = df.loc[df['load_dist'] == job_dist]
            cur_df = cur_df.loc[cur_df['miss_cost'] == miss_cost]
            for alpha in alpha_list:
                line_df = cur_df.loc[cur_df['compress_ratio'] == alpha]
                # line_df = line_df[~line_df.memory_ratio.isin(memory_ratio_deny_list)]
                cur_csv_name = 'tmp_perf_gain_{}_{}_{}.csv'.format(
                    miss_cost, alpha, job_dist)
                # print(line_df)
                # line_df = line_df.sort_values(by=['d_u'], ignore_index=True)
                line_df = line_df.sort_values(by=['memory_ratio'],
                                              ignore_index=True)
                # line_df.loc[line_df['zero_ac_lat_to_min_lat'] > 10, 'zero_ac_lat_to_min_lat'] = 10
                zac_line_df = line_df.loc[
                    line_df['zero_ac_lat_to_min_lat'] < 10]
                zac_line_df.to_csv(cur_csv_name, index=False)
                zac_line_tb = table(cur_csv_name)
                zpc_tb_csv_name = cur_csv_name.replace('.csv', '_zpc.csv')
                line_df.to_csv(zpc_tb_csv_name, index=False)
                zpc_line_tb = table(zpc_tb_csv_name)
                # print(cur_tb.dump())
                # p.line(cur_d,
                #        line_tb,
                #        xfield='memory_ratio',
                #        yfield='zero_ac_lat_to_min_lat',
                #        linecolor=alpha_color_str_dict[alpha],
                #        linedash=[2, 2],
                #        linewidth=0.8,
                #        legend=pic_id_legend_dict[pic_idx],
                #        legendtext=f'alpha={alpha:.1f}')
                # p.line(cur_d,
                #        line_tb,
                #        xfield='memory_ratio',
                #        yfield='zero_pc_lat_to_min_lat',
                #        linecolor=alpha_color_str_dict[alpha],
                #        linewidth=0.8)
                cur_line_attr_dict = get_gain_line_style(alpha)
                p.line(cur_d,
                       zac_line_tb,
                       xfield='memory_ratio',
                       yfield='zero_ac_lat_to_min_lat',
                       linecolor=alpha_color_str_dict[alpha],
                       linedash=[2, 2],
                       **cur_line_attr_dict)
                p.line(cur_d,
                       zpc_line_tb,
                       xfield='memory_ratio',
                       yfield='zero_pc_lat_to_min_lat',
                       linecolor=alpha_color_str_dict[alpha],
                       legend=pic_id_legend_dict[pic_idx],
                       legendtext=f'alpha={alpha:.1f}',
                       **cur_line_attr_dict)

                cur_point_attr_dict = get_gain_alpha_point_style(
                    alpha, alpha_color_str_dict[alpha])
                print(cur_point_attr_dict)
                # cur_point_attr_dict['style'] = 'vline'
                # cur_point_attr_dict['linecolor'] = alpha_color_str_dict[alpha]
                # cur_point_attr_dict['linewidth'] = 0.5
                # p.points(cur_d,
                #          line_tb,
                #          xfield='memory_ratio',
                #          yfield='zero_ac_lat_to_min_lat',
                #          **cur_point_attr_dict)
                cur_point_attr_dict = get_gain_alpha_point_style(
                    alpha, alpha_color_str_dict[alpha])
                p.points(cur_d,
                         zpc_line_tb,
                         xfield='memory_ratio',
                         yfield='zero_pc_lat_to_min_lat',
                         **cur_point_attr_dict)
                #  legend=pic_id_legend_dict[pic_idx],
                #  legendtext=f'alpha={alpha:.1f}',
                if do_remove_tmp_file():
                    os.remove(cur_csv_name)
                    os.remove(zpc_tb_csv_name)
                    pass
            # go to next pic
            pic_idx += 1
    last_d = pic_id_drawable_dict[num_pic - 1]
    print(f'last_d.right:{last_d.right()}')
    L.draw(c,
           coord=[last_d.right() - 8, last_d.bottom() + 30],
           width=3,
           height=3,
           fontsize=6,
           hspace=1,
           order=[0, 1, 2, 3, 4])
    c.text(coord=[last_d.right() + 4, last_d.top() - 16],
           text='dash:M_a=0',
           size=7)
    # Let's do the xaxis label at one shot here
    c.text(coord=[last_d.right() + 13, last_d.bottom() - 3],
           text='M/D_u',
           size=7,
           rotate=0)
    c.render()


def extract_alpha_list(list_str: str) -> List[float]:
    items = list_str.split(',')
    return [float(item) for item in items]


def print_usage(argv0):
    print(f'Usage: {argv0} <size|gain> <csv_name> <alpha_list>')


if __name__ == '__main__':
    if len(sys.argv) != 4:
        print_usage(sys.argv[0])
        sys.exit(1)
    y_type = sys.argv[1]
    csv_name = sys.argv[2]
    alpha_list = extract_alpha_list(sys.argv[3])
    if y_type == 'size':
        plot_best_size(csv_name, alpha_list)
    elif y_type == 'gain':
        plot_perf_gain(csv_name, alpha_list)
    else:
        print_usage(sys.argv[0])
        sys.exit(1)
