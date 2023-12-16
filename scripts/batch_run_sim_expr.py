#! /usr/bin/env python3

import datetime
import numpy as np
import math
import os
import sys
import subprocess
import time
from simulator_case_common import CacheExpCase

LOG_PROGRESS = True

CACHESTAT_ROOT_DIR = os.getenv("CACHESTAT_ROOT_DIR")
if CACHESTAT_ROOT_DIR is None:
    print(
        'CACHESTAT_ROOT_DIR environment variable does not exist. Please source or relogin'
    )
    print('Remember to run the setup_cache_sim.sh though')
    sys.exit(1)

# Put all the candidate expr set here, better make it cfg like thing though
# arg1: memory_ratio
# arg2: compression_ratio
# arg3: miss_cost
# arg4: distribution
EXP_SET1_CFG = {
    'arg1': [round(x, 4) for x in list(np.arange(0.1, 1.01, 0.05))],
    'arg2': [round(x, 4) for x in list(np.arange(0.1, 1.01, 0.05))],
    'arg3': [10, 50, 100],
    'arg4': [0, 1],
}
# print(EXP_SET1_CFG['arg1'])
# print(EXP_SET1_CFG['arg2'])

EXP_SET2_CFG = {
    'arg1': [0.8],
    'arg2': [0.5],
    'arg3': list(range(5, 101, 5)),
    'arg4': [0],
}
# print(EXP_SET2_CFG['arg3'])

EXP_SET3_CFG = {
    'arg1': [0.4, 0.5, 0.6, 0.7, 0.8],
    'arg2': [0.4, 0.5, 0.6],
    'arg3': list(range(5, 101, 5)),
    'arg4': [0, 1],
}
# print(EXP_SET3_CFG['arg3'])

EXP_SET4_CFG = {
    'arg1': [round(x, 4) for x in list(np.arange(0.1, 1.01, 0.05))],
    'arg2': [round(x, 4) for x in list(np.arange(0.1, 1.01, 0.05))],
    'arg3': [10, 50, 100],
    'arg4': [0],
    'trace_name_template':
        CACHESTAT_ROOT_DIR +
        '/ycsb-trace/get-scan-trace/roJob-hotspot_Na-2570000_HotOp-80_HotKey-20_MemRatio-{}_ScanPct-0.1_ScanMaxLen-20_ScanLenDist-uniform.out.trim.req.trace'
}

EXP_SET5_CFG = {
    'arg1': [0.4, 0.5, 0.6, 0.7, 0.8],
    'arg2': [0.2, 0.5],
    'arg3': list(range(10, 101, 10)),
    'arg4': [0],
    'trace_name_template':
        CACHESTAT_ROOT_DIR +
        '/ycsb-trace/get-scan-trace/roJob-hotspot_Na-2570000_HotOp-80_HotKey-20_MemRatio-{}_ScanPct-0.1_ScanMaxLen-20_ScanLenDist-uniform.out.trim.req.trace'
}
##########################################################################


def get_ts_str() -> str:
    return '{date:%Y-%m-%d:%H:%M:%S}'.format(date=datetime.datetime.now())


def get_log_name(num_host, cur_host_id, cur_host_num_core,
                 cur_host_num_case) -> str:
    cur_str = f'NumHost-{num_host}_Id-{cur_host_id}_NumCore'
    return cur_str + f'-{cur_host_num_core}_NumCase-{cur_host_num_case}.log'


def start_one_case(case: CacheExpCase):
    cmd = case.gen_cmd()
    print(f'==> Launch case: {case.gen_case_summary()}')
    p_case = subprocess.Popen(cmd, shell=True)
    return p_case


def exec_plan_one_host(host_id, case_list, num_core, logf=None):
    """
    Will keep number of inflight experiments <= num_core
    """
    start_ts_str = get_ts_str()
    running_case_process_dict = {}
    next_run_case_id = 0
    first_batch_num_case = min(num_core, len(case_list))
    rest_num_case = len(case_list) - first_batch_num_case

    # Start the initial batch
    for exec_id in range(first_batch_num_case):
        cur_case = case_list[next_run_case_id]
        cur_case_process = start_one_case(cur_case)
        running_case_process_dict[cur_case_process] = cur_case
        next_run_case_id += 1

    # Launch new if one finish
    while len(running_case_process_dict) > 0:
        done_process_list = []
        for cur_case_process, cur_case in running_case_process_dict.items():
            cur_case = running_case_process_dict[cur_case_process]
            if cur_case_process.poll() is not None:
                # one case terminated
                ret = cur_case_process.returncode
                case_str = cur_case.gen_case_summary()
                case_finish_str = f'==> Case finish (ret:{ret}): {case_str}'
                print(case_finish_str)
                # TODO: check returncode?
                done_process_list.append(cur_case_process)
                # Log the finish
                logf.write(case_finish_str + f' :{get_ts_str()}\n')
                logf.flush()
        for done_process in done_process_list:
            del (running_case_process_dict[done_process])
        # Launch more
        for i in range(len(done_process_list)):
            assert next_run_case_id <= len(case_list)
            if next_run_case_id == len(case_list):
                break
            cur_case = case_list[next_run_case_id]
            cur_case_process = start_one_case(cur_case)
            running_case_process_dict[cur_case_process] = cur_case
            next_run_case_id += 1
        assert len(running_case_process_dict) <= num_core
        # wait for two minutes
        time.sleep(120)

    end_ts_str = get_ts_str()
    print('==> All Done!')
    print(f'==> Start:{start_ts_str} end:{end_ts_str}')
    logf.flush()
    logf.close()


def run_batch_exprs(num_host: int, num_core_per_host: int, cur_host_id: int,
                    do_exec: bool):
    assert 0 <= cur_host_id < num_host
    # Calc expr plan
    #exp_set_list = [EXP_SET1_CFG, EXP_SET2_CFG]
    #exp_set_list = [EXP_SET3_CFG]
    #exp_set_list = [EXP_SET4_CFG]
    exp_set_list = [EXP_SET5_CFG]
    combine_factor_name = ['arg1', 'arg2', 'arg3', 'arg4']
    case_list = []
    for exp_set in exp_set_list:
        for a1 in exp_set['arg1']:
            for a2 in exp_set['arg2']:
                for a3 in exp_set['arg3']:
                    for a4 in exp_set['arg4']:
                        case_list.append(CacheExpCase(a1, a2, a3, a4))
                        if 'trace_name_template' in exp_set:
                            cur_trace_name = exp_set[
                                'trace_name_template'].format(
                                    round(float(a1), 3))
                            case_list[-1].set_input_trace_name(cur_trace_name)
    num_case = len(case_list)
    base_num_case_per_host = math.floor(num_case / num_host)
    num_diff = int(num_case - (base_num_case_per_host * num_host))
    assert num_diff >= 0
    host0_num_case = int(base_num_case_per_host + num_diff)
    print(f'Total number of cases to execute: {num_case}')
    output_str = f'Execution plan division: host0:{host0_num_case}'
    case_num_per_core = base_num_case_per_host / num_core_per_host
    host_num_case_list = [host0_num_case]
    for i in range(1, num_host):
        output_str += f' host{i}:{base_num_case_per_host}'
        host_num_case_list.append(base_num_case_per_host)
    print(output_str)
    print(f'Number of cases per core:{case_num_per_core:.5}')
    print(f'Current host (id:{cur_host_id})')
    print(f'    Total number of cases: {host_num_case_list[cur_host_id]}')
    avg_num_cases_per_core = host_num_case_list[cur_host_id] / num_core_per_host
    print(f'    Avg number of cases per core: {avg_num_cases_per_core:.3}')
    min_days_est = CacheExpCase.get_min_est_hour() * avg_num_cases_per_core / 24
    max_days_est = CacheExpCase.get_max_est_hour() * avg_num_cases_per_core / 24
    print(f'    Est days to finish: [{min_days_est:.3}, {max_days_est:.3}]')
    if not do_exec:
        return
    case_start_idx = 0
    for i in range(cur_host_id):
        case_start_idx += host_num_case_list[i]
    cur_host_case_list = case_list[case_start_idx:\
            case_start_idx +host_num_case_list[cur_host_id]]
    assert len(cur_host_case_list) == host_num_case_list[cur_host_id]
    if LOG_PROGRESS:
        logf = open(
            get_log_name(num_host, cur_host_id, num_core_per_host,
                         len(cur_host_case_list)), 'w')
    else:
        logf = None
    exec_plan_one_host(cur_host_id,
                       cur_host_case_list,
                       num_core_per_host,
                       logf=logf)


def print_usage(argv0: str):
    print(
        f'Usage {argv0} <NumHost> <CorePerHost> <CurHostId>(start from 0!) <T/t|F/f>(exec or not)'
    )


if __name__ == '__main__':
    if len(sys.argv) != 5:
        print_usage(sys.argv[0])
        sys.exit(1)
    nh = int(sys.argv[1])
    nc = int(sys.argv[2])
    cur_id = int(sys.argv[3])
    do_exec = sys.argv[4].lower() == 't'
    run_batch_exprs(nh, nc, cur_id, do_exec)
