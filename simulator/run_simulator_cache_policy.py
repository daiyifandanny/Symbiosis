import sys
import random
import LRUCache
import system
import file
import json
import statistics


max_page = 262144
distribution = 2
num_reads = 100000
num_trials = 10
f = file.File(0, max_page)
cache_size_ratio_list = [0.1 * x for x in range(1, 10, 1)]
cache_size_list = [int(262144 / 10 * x) for x in range(1, 10, 1)]
workload = list()

if distribution == 0:
    random.seed(210)
    for _ in range(0, num_reads * (num_trials + 1)):
        workload.append(random.randint(0, max_page - 1))
elif distribution == 1:
    random.seed(817)
    for _ in range(0, num_reads * (num_trials + 1)):
        target: int = None
        percentage: int = 20
        total: int = 100
        if random.randint(0, total - 1) < percentage:
            target = random.randint(0, int((max_page - 1) * (total - percentage) / total)) + \
                int((max_page - 1) * percentage / total)
        else:
            target = random.randint(0, int((max_page - 1) * percentage / total))
        workload.append(target)
elif distribution == 2:
    for line in open(sys.argv[1], "r").readlines():
        workload.append(int(line))


LRU_results = list()
for cache_size in cache_size_list:
    lru = LRUCache.LRUCache(cache_size)
    for i in range(cache_size, -1, -1):
        lru.Put((f.ino, i))
    
    single_size_list = list()
    for i in range(0, num_trials + 1, 1):
        num = 0
        hit = 0
        for request in workload[i * num_reads: (i + 1) * num_reads - 1]:
            if lru.Get((f.ino, request), True):
                hit += 1
            else:
                lru.Put((f.ino, request))
            num += 1
        if i > 0:
            print("{:.3f}".format(hit / num))
            single_size_list.append(hit / num)
    LRU_results.append((statistics.mean(single_size_list), statistics.stdev(single_size_list)))

pc_nra_results = list()
for cache_size in cache_size_list:
    kernel = system.Kernel(None, None, cache_size, 1, 1)
    for i in range(cache_size, -1, -1):
        kernel.cache.PutMany([((f.ino, i), 0, False, False, False)])
        
    single_size_list = list()
    for i in range(0, num_trials + 1, 1):
        num = 0
        hit = 0
        for request in workload[i * num_reads: (i + 1) * num_reads - 1]:
            if kernel.Simulate(f, request, 1):
                hit += 1
            num += 1
        if i > 0:
            print("{:.3f}".format(hit / num))
            single_size_list.append(hit / num)
    pc_nra_results.append((statistics.mean(single_size_list), statistics.stdev(single_size_list)))

pc_results = list()
for cache_size in cache_size_list:
    kernel = system.Kernel(None, None, cache_size, 1, 32)
    for i in range(cache_size, -1, -1):
        kernel.cache.PutMany([((f.ino, i), 0, False, False, False)])
    
    single_size_list = list()
    for i in range(0, num_trials, 1):
        num = 0
        hit = 0
        for request in workload[i * num_reads: (i + 1) * num_reads - 1]:
            if kernel.Simulate(f, request, 1):
                hit += 1
            num += 1
        if i > 0:
            print("{:.3f}".format(hit / num))
            single_size_list.append(hit / num)
    pc_results.append((statistics.mean(single_size_list), statistics.stdev(single_size_list)))
    
    
hit_ratio_dict = dict()
hit_ratio_dict["X-axis (M_cache:D)"] = cache_size_ratio_list
hit_ratio_dict["LRU"] = LRU_results
hit_ratio_dict["PageCache_no_Readahead"] = pc_nra_results
hit_ratio_dict["PageCache_Default"] = pc_results
with open(sys.argv[2], "w") as json_output:
    print(json.dumps(hit_ratio_dict, indent=4), file=json_output)


# markers = ["o", "x", "+"]
# font = {'weight' : 'bold',
#         'size'   : 16}
# matplotlib.rc('font', **font)
# pyplot.errorbar(cache_size_ratio_list, [x[0] for x in LRU_results], [x[1] for x in LRU_results], label="LRU", marker=markers[0])
# pyplot.errorbar(cache_size_ratio_list, [x[0] for x in pc_nra_results], [x[1] for x in pc_nra_results], label="PageCache_no_Readahead", marker=markers[1])
# pyplot.errorbar(cache_size_ratio_list, [x[0] for x in pc_results], [x[1] for x in pc_results], label="PageCache_Default", marker=markers[2])
# pyplot.ylabel("Hit Ratio", fontsize=16)
# pyplot.xlabel("Cache Size Ratio", fontsize=16)
# pyplot.ylim(bottom=0, top=1)
# pyplot.legend(fontsize=16)
# pyplot.grid()
# pyplot.show()
