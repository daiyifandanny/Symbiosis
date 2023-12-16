from application import AppCache
import sys
import statistics
import json
import random
import math
import system
import file


max_key = 262144
num_ops = 250000
max_ops = 11000000
num_repeats = 10
hashing = True
hashing_base = 18
heatup_cycle = 10
compression_ratio = 0.5
f = file.File(0, int(max_key * compression_ratio))
grouping_factor = 5
create_misalign = True
account_misalign = True
use_full_kernel = False
req_trace = False


def heatup(app_cache: AppCache, kernel_cache: AppCache, ssf):
    for i in range(0, max_key, 1):
        if hash(i >> grouping_factor) & ((1 << ssf) - 1) == 0:
            if not app_cache.Get(i, False):
                ret = app_cache.Put(i, 1 << ssf)
                if len(ret) != 0:
                    break

    for i in range(0, max_key, 1):
        if hash(i >> grouping_factor) & ((1 << ssf) - 1) == 0:
            if create_misalign:
                sys_start: int = int(i * compression_ratio - (1/4096 if i != 0 else 0))
            else:
                sys_start: int = int(i * compression_ratio)
            sys_size: int = int((i + 1 - 0.00001) * compression_ratio) - sys_start + 1
            
            if account_misalign:
                if use_full_kernel:
                    kernel_cache.Simulate(f, sys_start, sys_size)
                else:           
                    for j in range(sys_start, sys_start + sys_size, 1):
                        ret = list()
                        if not kernel_cache.Get(j, False):
                            size_factor = 1 if ssf == 0 or grouping_factor == 0 else \
                                (compression_ratio * (1 << grouping_factor)) / (compression_ratio * ((1 << grouping_factor)) + 2)
                            ret = kernel_cache.Put(j, (1 << ssf) * size_factor)
                            # ret = kernel_cache.Put(j, (1 << ssf))
                        if len(ret) != 0:
                            break
            else:
                assert not use_full_kernel
                if not kernel_cache.Get(i, False):
                    ret = kernel_cache.Put(i, (1 << ssf) * compression_ratio)
                    if len(ret) != 0:
                        break
            


def run_single(app_cache: AppCache, kernel_cache: AppCache, key, ssf):
    app_hit = None
    kernel_hit = True
    if hash(key >> grouping_factor) & ((1 << ssf) - 1) == 0:
        app_hit = app_cache.Get(key, True)
        if not app_hit:
            app_cache.Put(key, 1 << ssf)
            if create_misalign:
                sys_start: int = int(key * compression_ratio - (1/4096 if key != 0 else 0))
            else:
                sys_start: int = int(key * compression_ratio)
            sys_size: int = int((key + 1 - 0.00001) * compression_ratio) - sys_start + 1

            if account_misalign:
                if use_full_kernel:
                    if not kernel_cache.Simulate(f, sys_start, sys_size):
                        kernel_hit = False
                else:           
                    for j in range(sys_start, sys_start + sys_size, 1):
                        if not kernel_cache.Get(j, True):
                            size_factor = 1 if ssf == 0 or grouping_factor == 0 else \
                                (compression_ratio * (1 << grouping_factor)) / (compression_ratio * ((1 << grouping_factor)) + 2)
                            kernel_cache.Put(j, (1 << ssf) * size_factor)
                            # kernel_cache.Put(j, (1 << ssf))
                            kernel_hit = False
            else:
                assert not use_full_kernel
                if not kernel_cache.Get(key, False):
                    kernel_cache.Put(key, (1 << ssf) * compression_ratio)
                    kernel_hit = False
    return app_hit, kernel_hit


lines_temp = open(sys.argv[1], "r").readlines()
if req_trace:
    lines = [int(x) * max_key / 10000000 for x in lines_temp]
    print(len(lines))
else:
    lines = lines_temp
ssf_results = dict()
ssf_results2 = dict()
for ssf in range(0, 11, 1):    
    size_results = list()
    size_results2 = list()
    app_cache = AppCache(int(262144 * 0.0), 1, None)
    kernel_cache = AppCache(262144 - int(262144 * 0.0), 1, None)
    if use_full_kernel:
        kernel_cache = system.Kernel(None, None, 262144 - int(262144 * 0.0), 1, 32)
    heatup(app_cache, kernel_cache, ssf)
    for capacity in [int(x * 262144 / 10) for x in range(0, 11, 1)]:
        current = 0
        app_cache.ChangeSize(capacity, False, False)
        if use_full_kernel:
            kernel_cache.cache.ChangeSize(max(262144 - capacity, 256), False)
        else:
            kernel_cache.ChangeSize(262144 - capacity, False, True)
        heatup(app_cache, kernel_cache, ssf)
        single_results = list()
        single_results2 = list()
        
        # heatup
        while current < num_ops * heatup_cycle:
            run_single(app_cache, kernel_cache, int(lines[current % max_ops]), ssf)
            # run_single(app_cache, kernel_cache, random.randint(0, 262143), ssf)
            current += 1
        
        # run
        for i in range(heatup_cycle + 1, heatup_cycle + 1 + num_repeats, 1):
            num_app_miss = 0
            num_kernel_miss = 0
            while current < num_ops * i:
                ret = run_single(app_cache, kernel_cache, int(lines[current % max_ops]), ssf)
                # ret = run_single(app_cache, kernel_cache, random.randint(0, 262143), ssf)
                if ret[0] is not None and not ret[0]:
                    num_app_miss += 1
                    if not ret[1]:
                        num_kernel_miss += 1

                current += 1
            app_hit_ratio = max(1 - num_app_miss / num_ops * (1 << ssf), 0)
            kernel_hit_ratio = 0 if num_app_miss == 0 else 1 - num_kernel_miss / num_app_miss 
            # if ssf != 0:
            #     kernel_hit_ratio = min(1, 
            #         kernel_hit_ratio / math.floor(compression_ratio * (1 << grouping_factor)) * math.floor(compression_ratio * (1 << grouping_factor) + 1))
            single_results.append(app_hit_ratio)
            single_results2.append(kernel_hit_ratio)
            print("single: {:.4f} {:.4f} {} {}".format(app_hit_ratio, kernel_hit_ratio, num_kernel_miss, num_app_miss))
        size_results.append((round(statistics.mean(single_results), 4), round(statistics.stdev(single_results), 4)))
        size_results2.append((round(statistics.mean(single_results2), 4), round(statistics.stdev(single_results2), 4)))
        print("size: {:.2f} {:.4f} {:.4f}".format(capacity / 262144, 
            statistics.mean(single_results), statistics.stdev(single_results)))
        print("size: {:.2f} {:.4f} {:.4f}".format(1 - capacity / 262144, 
            statistics.mean(single_results2), statistics.stdev(single_results2)))
    ssf_results[ssf] = size_results
    ssf_results2[ssf] = size_results2
    print("ssf: {} ".format(ssf), end="")
    print(size_results)
    print(size_results2)
print(ssf_results)
print(ssf_results2)
with open(sys.argv[2], "w") as output:
    json.dump(ssf_results, output)
    print("", file=output)
    json.dump(ssf_results2, output)

