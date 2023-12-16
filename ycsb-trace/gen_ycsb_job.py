#! /usr/bin/env python3
"""
Would like to automatically generate ycsb load
"""

import numpy as np
import sys


def get_cfg_dict():
    cfg_dict = {
        'ARG_NUM_ACCESS': int(10 * 1000 * 1000),
        'ARG_MAX_KEY': int(10 * 1000 * 1000),
        'ARG_HOTSPOT_KEY_PCT': 0.2,
        'ARG_HOTSPOT_OP_PCT': 0.8,
    }
    return cfg_dict


def get_template_fname() -> str:
    return './workloads/ro-Job_sczipf.input'


def get_swot_template_fname() -> str:
    return './workloads/ro-swot.input'


def get_hotspot_template_fname() -> str:
    return './workloads/ro-hotspot.input'


def get_get_scan_template_fname() -> str:
    return './workloads/ro-get-scan.input'


def get_job_name_str(job_desc, num_access, max_key, hot_key_pct,
                     hot_op_pct) -> str:
    return f'ro-Job_{job_desc}-NumAccess_{int(num_access/1000/1000)}M-Maxkey_{int(max_key/1000/1000)}M-HotspotKeyPct-{int(100*hot_key_pct)}_HotspotOpPct-{int(hot_op_pct*100)}'


def get_swot_name_str(job_desc, num_access, max_key, hot_op_pct,
                      mem_ratio) -> str:
    t_str = '{}{}_{}M_{}'.format(job_desc, int(hot_op_pct * 100),
                                 int(num_access / 1000 / 1000), mem_ratio)
    return t_str


def get_get_scan_name_str(job_desc, num_access, max_bno, hot_op_pct,
                          hot_key_pct, mem_ratio, scan_proportion, scan_max_len,
                          scan_len_dist):
    t_str = 'roJob-{}_Na-{}_HotOp-{}_HotKey-{}_MemRatio-{}_ScanPct-{}_ScanMaxLen-{}_ScanLenDist-{}'.\
            format(job_desc, num_access, int(hot_op_pct*100), int(hot_key_pct*100), mem_ratio,
                    scan_proportion, scan_max_len, scan_len_dist)
    return t_str


def get_scan_must_key_list():
    return [
        'ARG_MAX_SCAN_LENGTH', 'ARG_SCAN_LEN_DIST', 'ARG_SCAN_PROPORTION',
        'ARG_READ_PROPORTION'
    ]


def gen_ycsb_job(template_name: str,
                 output_name: str,
                 num_access: int,
                 max_key: int,
                 hot_key_pct: float,
                 hot_op_pct: float,
                 req_dist=None,
                 scan_job_desc=None):
    cfg = get_cfg_dict()
    if req_dist is not None:
        assert req_dist in ['hotspot', 'uniform', 'zipfian']
        cfg['ARG_REQ_DIST'] = req_dist
    if scan_job_desc is not None:
        cfg.update(scan_job_desc)
        for k in get_scan_must_key_list():
            assert k in cfg
    cfg['ARG_NUM_ACCESS'] = num_access
    cfg['ARG_MAX_KEY'] = max_key
    cfg['ARG_HOTSPOT_KEY_PCT'] = hot_key_pct
    cfg['ARG_HOTSPOT_OP_PCT'] = hot_op_pct
    with open(template_name) as f:
        with open(output_name, 'w') as fw:
            for line in f:
                line = line.strip()
                arg_exist = 'ARG_' in line
                arg_resolve = False
                for k, v in cfg.items():
                    if k in line:
                        if 'PCT' in k:
                            cur_str = f'{v:.3}'
                        else:
                            cur_str = f'{v}'
                        line = line.replace(k, cur_str)
                        arg_resolved = True
                        break
                # We don't not allow any unresolved ARG_
                if arg_exist and not arg_resolved:
                    assert not arg_resolved
                fw.write(f'{line}\n')


def gen_contzipf_req_trace_job():
    hot_spots = [
        {
            'key_pct': 0.2,
            'op_pct': 0.8
        },
        {
            'key_pct': 0.3,
            'op_pct': 0.7,
        },
        {
            'key_pct': 0.1,
            'op_pct': 0.9,
        },
    ]
    N_1M = 1000 * 1000
    max_key_list = [
        N_1M * 10, N_1M * 20, N_1M * 25, N_1M * 40, N_1M * 50, N_1M * 80
    ]
    max_key_list = [int(v) for v in max_key_list]
    num_access_list = [int(N_1M * 10)]
    for hot_spot_pair in hot_spots:
        for num_access in num_access_list:
            for max_key in max_key_list:
                cur_output_name = get_job_name_str('contzipf', num_access,
                                                   max_key,
                                                   hot_spot_pair['key_pct'],
                                                   hot_spot_pair['op_pct'])
                gen_ycsb_job(get_template_fname(), cur_output_name, num_access,
                             max_key, hot_spot_pair['key_pct'],
                             hot_spot_pair['op_pct'])


def gen_contzipf_block_trace_job():
    hot_spots = [
        {
            'key_pct': 0.2,
            'op_pct': 0.8
        },
        {
            'key_pct': 0.1,
            'op_pct': 0.9
        },
    ]
    N_1M = 1000 * 1000
    N_1GB = 1024 * 1024 * 1024
    num_access_list = [int(N_1M * 11)]
    max_key_list = [int(N_1M * 10), int(N_1M * 50)]
    max_key_to_max_disk_byte = {
        int(N_1M * 10): int(N_1GB * 1),
        int(N_1M * 50): int(N_1GB) * 5,
    }
    for hot_spot_pair in hot_spots:
        for num_access in num_access_list:
            for max_key in max_key_list:
                cur_max_disk_byte = max_key_to_max_disk_byte[max_key]
                cur_output_name = get_job_name_str('contzipf', num_access,
                                                   max_key,
                                                   hot_spot_pair['key_pct'],
                                                   hot_spot_pair['op_pct'])
                gen_ycsb_job(get_template_fname(), cur_output_name, num_access,
                             max_key, hot_spot_pair['key_pct'],
                             hot_spot_pair['op_pct'])


def gen_hotspot_req_trace_job():
    hot_spots = [
        {
            'key_pct': 0.3,
            'op_pct': 0.7,
        },
        {
            'key_pct': 0.2,
            'op_pct': 0.8,
        },
        {
            'key_pct': 0.1,
            'op_pct': 0.9,
        },
    ]
    N_1M = 1000 * 1000
    num_access_list = [int(N_1M * 10)]
    max_key_list = [
        N_1M * 10,
        N_1M * 20,
        N_1M * 25,
        N_1M * 40,
        N_1M * 50,
        N_1M * 80,
    ]
    max_key_list = [int(m) for m in max_key_list]
    # max_key_to_max_disk_byte = {k:0 for k in max_key_list}
    for hot_spot_pair in hot_spots:
        for num_access in num_access_list:
            for max_key in max_key_list:
                # cur_max_disk_byte = max_key_to_max_disk_byte[max_key]
                cur_output_name = get_job_name_str('hotspot', num_access,
                                                   max_key,
                                                   hot_spot_pair['key_pct'],
                                                   hot_spot_pair['op_pct'])
                gen_ycsb_job(get_hotspot_template_fname(), cur_output_name,
                             num_access, max_key, hot_spot_pair['key_pct'],
                             hot_spot_pair['op_pct'])


def gen_swot_req_trace_job():
    hot_spots = [
        {
            'key_pct': 0.3,
            'op_pct': 0.7,
        },
        {
            'key_pct': 0.2,
            'op_pct': 0.8,
        },
        {
            'key_pct': 0.1,
            'op_pct': 0.9,
        },
    ]
    req_dist_list = ['uniform', 'zipfian', 'hotspot']
    N_1M = 1000 * 1000
    num_access_list = [int(N_1M * 10)]
    mem_ratio_list = [0.2, 0.4, 0.6, 0.8, 1]
    max_key_list = [N_1M * 10 / mem_ratio for mem_ratio in mem_ratio_list]
    #max_key_list = [
    #    N_1M * 10, N_1M * 20, N_1M * 25, N_1M * 40, N_1M * 50, N_1M * 80,
    #]
    max_key_list = [int(m) for m in max_key_list]
    # max_key_to_max_disk_byte = {k:0 for k in max_key_list}
    for req_dist in req_dist_list:
        for hot_spot_pair in hot_spots:
            for num_access in num_access_list:
                for idx, max_key in enumerate(max_key_list):
                    # cur_max_disk_byte = max_key_to_max_disk_byte[max_key]
                    cur_output_name = get_swot_name_str(req_dist, num_access,
                                                        max_key,
                                                        hot_spot_pair['op_pct'],
                                                        mem_ratio_list[idx])
                    print(cur_output_name)
                    gen_ycsb_job(get_swot_template_fname(), cur_output_name,
                                 num_access, max_key, hot_spot_pair['key_pct'],
                                 hot_spot_pair['op_pct'], req_dist)


def gen_get_scan_sim_job():
    N_1M = 1000 * 1000
    hot_spots = [
        {
            'key_pct': 0.2,
            'op_pct': 0.8,
        },
    ]
    req_dist_list = ['hotspot']
    # req_dist_list = ['uniform', 'zipfian', 'hotspot']
    scan_len_dist_list = ['uniform']
    # scan_len_list = ['zipfian', 'uniform']
    scan_max_len_list = [20]
    scan_proportion_list = [0.1]
    num_access_list = [int(N_1M * 2.57)]
    mem_ratio_list = [round(x, 4) for x in list(np.arange(0.1, 1.01, 0.05))]
    NUM_PAGES = 262144
    max_bno_list = [NUM_PAGES / mem_ratio for mem_ratio in mem_ratio_list]
    max_bno_list = [int(m) for m in max_bno_list]
    print(max_bno_list)
    for req_dist in req_dist_list:
        for hot_spot_pair in hot_spots:
            for num_access in num_access_list:
                for scan_max_len in scan_max_len_list:
                    for scan_len_dist in scan_len_dist_list:
                        for scan_proportion in scan_proportion_list:
                            read_proportion = 1 - scan_proportion
                            for idx, max_bno in enumerate(max_bno_list):
                                cur_output_name = get_get_scan_name_str(
                                    req_dist, num_access, max_bno,
                                    hot_spot_pair['op_pct'],
                                    hot_spot_pair['key_pct'],
                                    mem_ratio_list[idx], scan_proportion,
                                    scan_max_len, scan_len_dist)
                                cur_scan_cfg_dict = {
                                    'ARG_MAX_SCAN_LENGTH': scan_max_len,
                                    'ARG_SCAN_LEN_DIST': scan_len_dist,
                                    'ARG_SCAN_PROPORTION': scan_proportion,
                                    'ARG_READ_PROPORTION': read_proportion,
                                }
                                print(cur_output_name)
                                gen_ycsb_job(get_get_scan_template_fname(),
                                             cur_output_name,
                                             num_access,
                                             max_bno,
                                             hot_spot_pair['key_pct'],
                                             hot_spot_pair['op_pct'],
                                             req_dist=req_dist,
                                             scan_job_desc=cur_scan_cfg_dict)


if __name__ == '__main__':
    #gen_contzipf_req_trace_job()
    #gen_contzipf_block_trace_job()
    #gen_hotspot_req_trace_job()
    #gen_swot_req_trace_job()
    gen_get_scan_sim_job()
