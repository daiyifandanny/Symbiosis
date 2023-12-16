from ctypes import resize
from enum import Enum
import simpy
import cache
import typing
import stats
from file import File
from device import BlockDevice
import math
import adapter


class ReadState(Enum):
    NONE = 0
    RANDOM = 1
    SYNC = 2
    ASYNC = 3
    BOTH = 4


class System(object):
    pass

class Kernel(object):
    pass


class Readahead(object):
    def __init__(self, max_readahead: int, page_cache: Kernel) -> None:
        self.prev_index: int = None
        self.start_index: int = None
        self.lookahead_index: int = None
        self.max_readahead: int = max_readahead
        self.current_readahead: int = None
        self.current_ra_type: int = 0
        self.page_cache: Kernel = page_cache
        
    
    def Clear(self) -> None:
        self.start_index = None
        self.lookahead_index = None
        self.current_readahead = None
    
    
    def Reset(self, target: int, init: bool = True) -> None:
        if init:
            self.current_readahead = self.InitRaValue(size=1)
        self.start_index = target
        self.lookahead_index = target + (self.current_readahead // 4 if self.current_readahead >= 4 else 1)

    
    def InitRaValue(self, size: int) -> int:
        new_size = 2 ** math.ceil(math.log2(size))
        if new_size <= self.max_readahead / 32:
            new_size *= 4
        elif new_size <= self.max_readahead / 4:
            new_size *= 2
        else:
            new_size = self.max_readahead
        return new_size
        
    
    def NextRaValue(self) -> int:
        # return true if limited by max
        ret: int = self.current_readahead
        if ret < self.max_readahead / 16:
            ret *= 4
        else:
            ret = min(self.max_readahead, ret * 2)
        return ret
    

    def AssignRaValue(self, value: int) -> None:
        self.current_readahead = min(value, self.max_readahead)

    
    def AdvanceReadahead(self) -> None:
        self.Reset(self.readahead_index, init=False)
    
    
    def CheckMarksAndReadahead(self, target: int) -> bool:
        # return if a readahead is issued
        if target == self.lookahead_index or target == self.readahead_index:
            # if target == self.lookahead_index:
            #     self.AdjustRaValue(increase=True)
            self.AdjustRaValue(increase=True)
            self.AdvanceReadahead()
            return True
        else:
            return False
    
    
    def Update(self, file: int, target: int, size: int, mark_hit: bool, activate: bool) -> None:
        seq_length: int = target - self.page_cache.FindClosestNonexistanceBefore(file, target, self.max_readahead) - 1
        if self.max_readahead == 1:
            self.current_ra_type = 6
            stats.s.ra_type_nums[self.current_ra_type] += 1
            self.page_cache.SubmitRead(file, target, 1, True, target, self, activate)
            return

        if target == 0:
            # initial readahead
            self.start_index = target
            self.current_readahead = self.InitRaValue(size)
            self.lookahead_index = self.start_index + (size if self.current_readahead > size else 0)
            self.current_ra_type = 0
            stats.s.ra_type_nums[self.current_ra_type] += 1
        
        elif self.start_index is not None and \
            (target == self.start_index + self.current_readahead or \
            (target == self.lookahead_index and True)):
            # sync & async ra mark hit
            self.start_index += self.current_readahead
            self.current_readahead = self.NextRaValue()
            self.lookahead_index = self.start_index
            self.current_ra_type = 4 if mark_hit else 1
            stats.s.ra_type_nums[self.current_ra_type] += 1
        
        elif mark_hit:
            # async ra mark hit wihtout proper context
            start:int = self.page_cache.FindClosestNonexistanceAfter(file, target, self.max_readahead)
            if start - target == self.max_readahead + 1:
                start -= 1
            if start - target > self.max_readahead:
                return ReadState.NONE
            
            self.start_index = start
            self.current_readahead = start - target
            self.current_readahead += size
            self.current_readahead = self.NextRaValue()
            self.lookahead_index = self.start_index
            self.current_ra_type = 5
            stats.s.ra_type_nums[self.current_ra_type] += 1
            stats.s.contextual_async_length += start - target
        
        elif size > self.max_readahead:
            self.start_index = target
            self.current_readahead = self.max_readahead
            self.lookahead_index = self.start_index

        elif self.prev_index is not None and (target - self.prev_index <= 1 and target >= self.prev_index):
            # sync linear detection
            self.start_index = target
            self.current_readahead = self.InitRaValue(size)
            self.lookahead_index = self.start_index + (size if self.current_readahead > size else 0)
            self.current_ra_type = 2
            stats.s.ra_type_nums[self.current_ra_type] += 1

        elif seq_length > size:
            # sync contextual linear
            if seq_length >= target:
                seq_length *= 2
            self.start_index = target
            self.AssignRaValue(seq_length + size)
            self.lookahead_index = self.start_index + self.current_readahead - 1 # idk why not just 1
            self.current_ra_type = 3
            stats.s.ra_type_nums[self.current_ra_type] += 1
            stats.s.contextual_sync_length += seq_length + 1

        else:
            # random read
            self.current_ra_type = 6
            stats.s.ra_type_nums[self.current_ra_type] += 1
            self.page_cache.SubmitRead(file, target, size, True, target, self, activate)
            return

        if target == self.start_index and self.lookahead_index == self.start_index:
            next_ra:int = self.NextRaValue()
            if self.current_readahead + next_ra <= self.max_readahead:
                self.lookahead_index += self.current_readahead
                self.current_readahead += next_ra
            else:
                self.current_readahead = self.max_readahead
                self.lookahead_index += self.max_readahead // 2
        
        self.page_cache.SubmitRead(file, self.start_index, self.current_readahead, not mark_hit, target, self, activate)
        return
                      

class Kernel(object):
    def __init__(self, env: simpy.Environment, sys: System, size: int, hit_cost: float, readahead_value: int) -> None:
        self.env: simpy.Environment = env
        self.sys: System = sys
        self.cache: cache.PageCache = cache.PageCache(size, env)
        self.hit_cost: int = hit_cost
        self.async_cost: int = hit_cost
        self.max_readahead: int = readahead_value
        self.readahead_structures: typing.Dict(int, Readahead) = dict()
        
    
    def FindClosestExistanceBefore(self, file: int, target: int, depth: int) -> int:
        i: int = max(target - min(depth, 1), 0)
        for i in range(target - 1, max(0, target - depth) - 1, -1):
            if self.cache.Get((file.ino, i), False) is not None:
                return i
        return i - 1


    def FindClosestExistanceAfter(self, file: int, target: int, depth: int) -> int:
        i: int = min(target + min(depth, 1), file.size - 1)
        for i in range(target + 1, min(file.size - 1, target + depth) + 1, 1):
            if self.cache.Get((file.ino, i), False) is not None:
                return i
        return i + 1
    

    def FindClosestNonexistanceBefore(self, file: int, target: int, depth: int) -> int:
        i: int = max(target - min(depth, 1), 0)
        for i in range(target - 1, max(0, target - depth) - 1, -1):
            if self.cache.Get((file.ino, i), False) is None:
                return i
        return i - 1


    def FindClosestNonexistanceAfter(self, file: int, target: int, depth: int) -> int:
        i: int = min(target + min(depth, 1), file.size - 1)
        for i in range(target + 1, min(file.size - 1, target + depth) + 1, 1):
            if self.cache.Get((file.ino, i), False) is None:
                return i
        return i + 1
    
    
    def SubmitRead(self, file: File, start: int, size: int, sync: bool, target: int, ra_struct: Readahead, activate: bool) -> bool:
        # sync should be only for stats now
        # calculate actual read request
        if start >= file.size:
            return self.env.timeout(0) if self.env is not None else None

        # read only missing pages
        num_requests: int = 0
        current_page_count: int = 0
        page_count: int = 0
        args: list[tuple[tuple[int, int], int, bool, bool]] = list()
        for i in range(start, min(start + size, file.size)):
            if self.cache.Get((file.ino, i), False) is not None:
                if current_page_count > 0:
                    num_requests += 1
                    arrival_list: list[int] = self.sys.disk.Read(i -  current_page_count, current_page_count) \
                        if self.sys is not None else [0] * current_page_count
                    for index, j in enumerate(range(i - current_page_count, i)):
                        args.append(((file.ino, j), arrival_list[index], j == target, j == ra_struct.lookahead_index, activate))
                    current_page_count = 0
                continue

            current_page_count += 1
            page_count += 1
            
        i += 1
        if current_page_count > 0:
            num_requests += 1
            arrival_list: list[int] = self.sys.disk.Read(i -  current_page_count, current_page_count) \
                if self.sys is not None else [0] * current_page_count
            for index, j in enumerate(range(i - current_page_count, i)):
                args.append(((file.ino, j), arrival_list[index], j == target, j == ra_struct.lookahead_index, activate))
        
        if page_count > self.max_readahead:
            assert False

        self.cache.PutMany(args)


        # stats
        if self.sys is not None and page_count != 0:
            if sync:
                stats.s.sync_pages += page_count
                stats.s.sync_num += num_requests
                stats.s.sync_ra += 1
                stats.s.readahead_pages += page_count - 1 # 1 is req_size
            else:
                stats.s.async_pages += page_count
                stats.s.async_num += num_requests
                stats.s.async_ra += 1
                stats.s.readahead_pages += page_count
            stats.s.ra_type_pages[ra_struct.current_ra_type] += page_count

    
    def Simulate(self, file: File, start: int, size: int):
        real_size: int = min(size, file.size - start)
        cache_hit: bool = True
        for i in range(0, real_size):
            target = start + i
            current_size = real_size - i

            # check cache
            cache_item: cache.CacheItem = self.cache.Get((file.ino, target), reference=True)
            
            # get ra struct
            ra_struct: Readahead = None
            if file.ino not in self.readahead_structures:
                ra_struct = Readahead(self.max_readahead, self)
                self.readahead_structures[file.ino] = ra_struct
            else:
                ra_struct = self.readahead_structures[file.ino]

            if cache_item is None:
                # cache miss, go to disk, then come back to fetch in page cache
                ra_struct.Update(file, target, current_size, False, False)
                cache_item = self.cache.Get((file.ino, target), reference=True)
                cache_hit = False

            if cache_item is None:
                ra_struct.Update(file, target, current_size, False, False)
                cache_item = self.cache.Get((file.ino, target), reference=True)

            if cache_item is None:
                assert False
            
            # update ra and possible async ra issue
            # if cache_item.mark or target == ra_struct.lookahead_index or \
            #         target == ra_struct.start_index + ra_struct.current_readahead:
            if cache_item.mark:
                cache_item.mark = False
                ra_struct.Update(file, target, current_size, True, False)
            
            # update ra prev_index
            ra_struct.prev_index = target

        return cache_hit       
        
    def Read(self, file: File, start: int, size: int, activate: bool):
        real_size: int = min(size, file.size - start)
        hit_cost: int = int(self.hit_cost * real_size)
        stats.s.system_cost += hit_cost
        yield self.env.timeout(hit_cost)

        if self.cache.capacity == 0:
            finished = 0
            while finished < real_size:
                this_size = min(real_size - finished, self.max_readahead)
                yield self.env.timeout(self.sys.disk.Read(start + finished, this_size)[0] - self.env.now)
                finished += this_size
                stats.s.page_cache_miss_num += 1

        else:
            cache_hit: bool = True
            for i in range(0, real_size):
                target = start + i
                current_size = real_size - i

                # check cache
                cache_item: cache.CacheItem = self.cache.Get((file.ino, target), reference=True)

                # exp
                # if real_size == 1:
                #     if cache_item is not None:
                #         stats.s.one_page_hit_num += 1
                #     else:
                #         stats.s.one_page_miss_num += 1
                # elif real_size == 2 and i == 0:
                #     if cache_item is not None:
                #         stats.s.first_page_hit_num += 1
                #         if self.cache.Get((file.ino, target + 1), reference=False) is not None:
                #             stats.s.second_page_hit_num += 1
                #         else:
                #             stats.s.second_page_miss_num += 1                        
                #     else:
                #         stats.s.first_page_miss_num += 1

                # get ra struct
                ra_struct: Readahead = None
                if file.ino not in self.readahead_structures:
                    ra_struct = Readahead(self.max_readahead, self)
                    self.readahead_structures[file.ino] = ra_struct
                else:
                    ra_struct = self.readahead_structures[file.ino]

                if cache_item is None:
                    # cache miss, go to disk, then come back to fetch in page cache
                    ra_struct.Update(file, target, current_size, False, activate)
                    cache_item = self.cache.Get((file.ino, target), reference=True)
                    cache_hit = False

                if cache_item is None:
                    ra_struct.Update(file, target, current_size, False, activate)
                    cache_item = self.cache.Get((file.ino, target), reference=True)
                    cache_hit = False

                if cache_item is None:
                    assert False

                # stat
                if cache_item.readahead and cache_item.ref_count == 1:
                    stats.s.readahead_hits += 1

                # wait for arrival
                arrival_time: int = cache_item.arrival
                current_time = self.env.now
                if arrival_time > current_time:
                    cache_hit = False
                    stats.s.system_cost += arrival_time - current_time
                    yield self.env.timeout(arrival_time - current_time)

                # update ra and possible async ra issue
                # if cache_item.mark or target == ra_struct.lookahead_index or \
                #         target == ra_struct.start_index + ra_struct.current_readahead:
                if cache_item.mark:
                    cache_item.mark = False
                    stats.s.ra_cleared += 1
                    ra_struct.Update(file, target, current_size, True, activate)
                
                # update ra prev_index
                ra_struct.prev_index = target
            
            # stats
            if cache_hit:
                stats.s.page_cache_hit_num += 1
            else:
                stats.s.page_cache_miss_num += 1
            adapter.a.Record(file, start, size, app=False, hit=cache_hit)


class System(object):
    def __init__(self, env: simpy.Environment, page_cache_size: int, page_cache_hit_cost: float, 
                 default_readahead: int, seq_single_latency: int, rand_single_latency: int) -> None:
        self.env: simpy.Environment = env
        self.disk: BlockDevice = BlockDevice(self.env, seq_single_latency, rand_single_latency)
        self.page_cache: Kernel = Kernel(self.env, self, page_cache_size, page_cache_hit_cost, default_readahead)
        
    
    def Read(self, file: File, target: int, size: int, activate: bool):
        for g in self.page_cache.Read(file, target, size, activate):
            yield g
