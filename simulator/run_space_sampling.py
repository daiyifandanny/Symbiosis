from application import AppCache
import sys
import statistics
import json


max_key = 262144
num_ops = 1000000
max_ops = 10000000
num_repeats = 10
hashing = False
hashing_base = 18


def heatup(cache: AppCache, ssf):
    for i in range(0, max_key, 1 << ssf):
        ret = cache.Put(i, 1 << ssf)
        if len(ret) != 0:
            break


def run_single(cache: AppCache, key, ssf) -> bool:
    if ssf == 0:
        pass
    elif hashing:
        key = hash(key)
        if key < 0:
            key = -key
        key = (key & ((1 << (hashing_base - ssf)) - 1)) << ssf
    else:
        key = (key >> ssf) << ssf
    hit = cache.Get(key, True)
    if not hit:
        cache.Put(key, 1 << ssf)
    return hit


lines = open(sys.argv[1], "r").readlines()
ssf_results = dict()
for ssf in range(0, 13, 1):    
    size_results = list()
    for capacity in [int(x * 262144 / 10) for x in range(1, 11, 1)]:
        current = 0
        cache = AppCache(capacity, 1, None)
        single_results = list()
        
        # heatup
        heatup(cache, ssf)
        while current < num_ops * 1:
            run_single(cache, int(lines[current % max_ops]), ssf)
            current += 1
        
        # run
        for i in range(2, 2 + num_repeats, 1):
            num_hit = 0
            while current < num_ops * i:
                if run_single(cache, int(lines[current % max_ops]), ssf):
                    num_hit += 1
                current += 1
            single_results.append(num_hit / num_ops)
            print("single: {:.4f}".format(num_hit / num_ops))
        size_results.append((round(statistics.mean(single_results), 4), round(statistics.stdev(single_results), 4)))
        print("size: {:.2f} {:.4f} {:.4f}".format(capacity / 262144, 
            statistics.mean(single_results), statistics.stdev(single_results)))
    ssf_results[ssf] = size_results
    print("ssf: {} ".format(ssf), end="")
    print(size_results)
print(ssf_results)
with open(sys.argv[2], "w") as output:
    json.dump(ssf_results, output)


