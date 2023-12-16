import system
import simpy
import random
import argparse
import stats
from file import File
import application
import adapter
import numpy
import math


# constants
base_dir = "/home/yifan/research/cache/"

# traces
step_time = open("step_time.txt", "w")
heatup_trace = open("heatup_trace.txt", "w")



class Workload(object):
    def __init__(self, env: simpy.Environment, app: application.Application, sys: system.System, trace_filename: str, 
            sizetrace_filename: str, read_size: int, max_pages: int, num_reads: int, distribution: int, ratio: float) -> None:
        self.num_reads: int = num_reads
        self.env: simpy.Environment = env
        self.app: application.Application = app
        self.sys: system.System = sys
        self.max_pages: int = max_pages
        self.trace_filename = trace_filename
        self.sizetrace_filename = sizetrace_filename
        self.read_size = read_size
        self.distribution = distribution
        self.ratio = ratio
        self.num_keys = 10485760
        self.app_unit_divider = self.num_keys / self.max_pages
    
    
    def run(self, step: int):
        file: File = File(0, int(self.max_pages * self.ratio))
        start_timestamp = self.env.now
        if step != 0:
            # sequential
            for i in range(0, self.max_pages, step):
                for g in self.app.Read(file, i, self.read_size):
                    yield g
        
        elif self.trace_filename != "none":
            # trace read
            for i in open(self.trace_filename, "r").readlines():
                # self.sys.Read(random.randint(0, system.max_pages - 1))
                target_app_unit = int(i)
                assert(target_app_unit < self.max_pages)
                for g in self.app.Read(file, target_app_unit, self.read_size):
                    yield g

            # last: int = self.env.now
            # count: int = 0
            # if self.distribution == 1:
            #     self.trace_filename = self.trace_filename[:-5] + "2.txt"
            # with open(self.trace_filename, "r") as trace_file:
            #     for i, line in enumerate(trace_file.readlines()):
            #         if count >= self.num_reads:
            #             break
            #         target = int(line.split()[0])
            #         for g in self.sys.Read(file, target, self.read_size, False):
            #             yield g
            #         count += 1

                    # print(self.env.now - last, file=step_time)
                    # last = self.env.now

                    # if (i + 1) % 10000 == 0:
                    #     diff = self.env.now - start_timestamp
                    #     print("Time {} Kernel_Ratio {:.2f} Kernel_Size {} Kernel_Capacity {} App_Ratio {:.2f} App_Size {} App_Capacity {}"
                    #         .format(diff, stats.s.Kernel_Ratio(),self.sys.page_cache.cache.Size(), self.sys.page_cache.cache.capacity,
                    #                 stats.s.App_Ratio(), self.app.cache.size, self.app.cache.capacity))
                    #     stats.s.ClearCacheStats()
                    #     start_timestamp = self.env.now
        
        elif self.sizetrace_filename != "none":
            # sizetrace read
            last: int = self.env.now
            count: int = 0
            with open(self.sizetrace_filename, "r") as trace_file:
                targets_raw: list[int] = list()
                sizes_raw: list[int] = list()
                for index, line in enumerate(trace_file.readlines()):
                    # if index >= self.num_reads:
                    #     break
                    targets_raw.append(int(line.split()[0]))
                    sizes_raw.append(int(line.split()[1]))

                ratio = 1 # self.max_pages / max(targets_raw)
                targets = [int(x * ratio) for x in targets_raw]
                sizes = [x if x == 1 else int(x * ratio) for x in sizes_raw]

                for target, size in zip(targets, sizes):
                    for g in self.app.Read(file, target, size):
                        yield g
                    print(self.env.now - last, file=step_time)
                    last = self.env.now

        elif self.distribution == 1:
            # zipfian
            random.seed(912)
            for i in range(0, self.num_reads):
                target: int = None
                percentage: int = 20
                total: int = 100
                if random.randint(0, total - 1) < percentage:
                    target = random.randint(0, int((self.max_pages - 1) * (total - percentage) / total)) + \
                        int(self.max_pages - 1) * percentage / total
                else:
                    target = random.randint(0, int((self.max_pages - 1) * percentage / total))

                for g in self.app.Read(file, int(target), self.read_size):
                    yield g
                
                # if (i + 1) % 10000 == 0:
                #     diff = self.env.now - start_timestamp
                #     print("Time {} Kernel_Ratio {:.2f} Kernel_Size {} Kernel_Capacity {} App_Ratio {:.2f} App_Size {} App_Capacity {}"
                #         .format(diff, stats.s.Kernel_Ratio(),self.sys.page_cache.cache.Size(), self.sys.page_cache.cache.capacity,
                #                 stats.s.App_Ratio(), self.app.cache.size, self.app.cache.capacity), file=heatup_trace)
                #     stats.s.ClearCacheStats()
                #     start_timestamp = self.env.now
        
        else:
            # random
            random.seed(210)
            for i in range(0, self.num_reads):
                # self.sys.Read(random.randint(0, system.max_pages - 1))
                target_key = random.randint(0, self.num_keys - 1)
                target_app_unit = math.floor(int(target_key / self.app_unit_divider))
                assert(target_app_unit < self.max_pages)
                for g in self.app.Read(file, target_app_unit, self.read_size):
                    yield g
                
                # if (i + 1) % 10000 == 0:
                #     diff = self.env.now - start_timestamp
                #     print("Time {} Kernel_Ratio {:.2f} Kernel_Size {} Kernel_Capacity {} App_Ratio {:.2f} App_Size {} App_Capacity {}"
                #         .format(diff, stats.s.Kernel_Ratio(),self.sys.page_cache.cache.Size(), self.sys.page_cache.cache.capacity,
                #                 stats.s.App_Ratio(), self.app.cache.size, self.app.cache.capacity), file=heatup_trace)
                #     stats.s.ClearCacheStats()
                #     start_timestamp = self.env.now
                
                # if i == self.num_reads / 4:
                #     self.app.cache.ChangeSize(self.max_pages - 256, False)


if __name__ == "__main__":
    parser: argparse.ArgumentParser = argparse.ArgumentParser()
    parser.add_argument("--ratio", type=float, default=0.5, required=False)
    parser.add_argument("--memory_size", type=float, default=1, required=False)
    parser.add_argument("--page_cache_size", type=float, default=1, required=False)
    parser.add_argument("--page_cache_exact", type=int, default=0, required=False)
    parser.add_argument("--page_cache_hit_cost", type=float, default=1, required=False)
    parser.add_argument("--app_hit_cost", type=float, default=1, required=False)
    parser.add_argument("--app_miss_cost", type=float, default=5, required=False)
    parser.add_argument("--compression_cost", type=float, default=20, required=False)
    parser.add_argument("--ra", type=int, default=32, required=False)
    parser.add_argument("--seq_disk_latency", type=int, default=20, required=False)
    parser.add_argument("--rand_disk_latency", type=int, default=100, required=False)
    parser.add_argument("--num_reads", type=int, default=5000000, required=False)
    parser.add_argument("--max_pages", type=int, default=262144, required=False)
    parser.add_argument("--read_size", type=int, default=1, required=False)
    parser.add_argument("--step", type=int, default=0, required=False)
    parser.add_argument("--distribution", type=int, default=0, required=False) # 1 = zipfian
    # parser.add_argument("--trace", type=str, default=base_dir + "trace.txt", required=False)
    parser.add_argument("--trace", type=str, default="none", required=False)
    parser.add_argument("--sizetrace", type=str, default="none", required=False)
    parser.add_argument("--preload", type=bool, default=True, required=False)
    args: argparse.Namespace = parser.parse_args()
    
    page_cache_size: int = int(args.max_pages * args.page_cache_size) if args.page_cache_exact == 0 else args.page_cache_exact
    # page_cache_size = max(page_cache_size + 1, 256)
    app_cache_size: int = int(args.memory_size * args.max_pages - page_cache_size)
    max_pages: int = args.max_pages

    env: simpy.Environment = simpy.Environment()
    sys: system.System = system.System(env, int(args.memory_size * args.max_pages) + 1 if page_cache_size != 0 else 0,
                                       args.page_cache_hit_cost, args.ra, args.seq_disk_latency, args.rand_disk_latency)
    app: application.Application = application.Application(args.app_hit_cost, args.app_miss_cost, app_cache_size, args.ratio, env, sys.page_cache)                                   
    workload: Workload = Workload(env, app, sys, args.trace, args.sizetrace, args.read_size, max_pages, args.num_reads, args.distribution, args.ratio)
    adapter.a.FillParameter(args.app_miss_cost, args.rand_disk_latency, int(args.memory_size * args.max_pages), app.cache, sys.page_cache, max_pages)

    # if args.preload:
    #     numpy.random.seed(811)

    #     for i in numpy.random.permutation(max_pages):
    #         ret = app.cache.Put((0, i), 1, True)
    #         if len(ret) != 0:
    #             break
        
    #     if page_cache_size != 0:
    #         for i in numpy.random.permutation(int(args.max_pages * args.ratio)):
    #         # for i in range(0, int(args.max_pages * args.ratio)):
    #             ret = sys.page_cache.cache.PutMany([((0, i), 0, False, False, False)])
    #             if ret != 0:
    #                 break
    
    stats.s.ClearCacheStats()
    env.process(workload.run(args.step))
    env.run()

    stats.s.Calculate(sys.page_cache.cache, env)
    print(stats.s.__dict__)
