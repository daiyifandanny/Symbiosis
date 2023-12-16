import typing
from collections import OrderedDict
import simpy
from file import File
import system
import stats
import adapter
import math


class AppCacheItem:
    def __init__(self, size) -> None:
        self.ref_count: int = 0
        self.size: float = size


class AppCache(object):
    def __init__(self, capacity: int, ratio: float, page_cache) -> None:
        self.capacity: int = capacity
        self.size: float = 0
        self.ratio: float = ratio
        self.cache: typing.OrderedDict[tuple[int, int], AppCacheItem] = OrderedDict()
        self.page_cache = page_cache
    
    
    def ChangeSize(self, size : int, delta : bool, top: bool = False) -> None:
        if delta:
            self.capacity += size
        else:
            self.capacity = size
        
        if not top:
            while math.floor(self.Size()) > self.capacity:
                self.Evict()
        else:
            while math.floor(self.Size()) > self.capacity:
                evicted: tuple[tuple[int, int], AppCacheItem] = self.cache.popitem(last=True)
                self.size -= evicted[1].size


    def Size(self) -> float:
        return self.size
    

    def Evict(self) -> tuple[tuple[int, int], AppCacheItem]:
        adapter.a.CacheFilled(app=True)
        evicted: tuple[tuple[int, int], AppCacheItem] = self.cache.popitem(last=False)
        self.size -= evicted[1].size
        return evicted

    
    def Ref(self, key: tuple[int, int]) -> None:
        if key in self.cache:
            item = self.cache.pop(key)
            self.cache[key] = item
    

    def Put(self, key: tuple[int, int], size: float, affect_page_cache: bool = False) -> list[tuple[tuple[int, int], AppCacheItem]]:
        assert key not in self.cache
        self.cache[key] = AppCacheItem(size)
        original_size = self.size
        self.size += size
        
        ret = list()
        while math.floor(self.Size()) > self.capacity:
            # buggy need fix
            ret.append(self.Evict())
        
        if affect_page_cache:
            self.page_cache.cache.ChangeSize(original_size - self.Size(), True)
        return ret
    

    def Get(self, key: tuple[int, int], reference: bool) -> bool:
        ret: bool = False
        if key in self.cache:
            ret = True
            if reference:
                self.Ref(key)
        return ret


class Application(object):
    def __init__(self, hit_cost: float, miss_penalty: int, capacity: int, ratio: float, env: simpy.Environment, page_cache) -> None:
        self.hit_cost: int = hit_cost
        self.miss_penalty: int = miss_penalty
        self.cache: AppCache = AppCache(capacity, ratio, page_cache)
        self.ratio = ratio
        self.env: simpy.Environment = env
        self.page_cache = page_cache # could be page_cache

    
    def Simulate(self, file: File, start: int, size: int):
        cache_hit: bool = True
        pc_cache_hit: bool = True
        if self.cache.Get((file.ino, start), True):
            pass
        else:
            pc_cache_hit = self.page_cache.Simulate(file, start, size)
            self.cache.Put((file.ino, start), size)
            cache_hit = False
        return cache_hit, pc_cache_hit   

    
    def Read(self, file: File, start: int, size: int):        
        stats.s.app_cost += self.hit_cost
        yield self.env.timeout(self.hit_cost)

        # sys_start: int = int(start * self.ratio)
        # sys_size: int = int((start + size - 1) * self.ratio) - sys_start + 1
        # for g in self.page_cache.Read(file, sys_start, sys_size, activate=False):
        #     yield g
        # return

        cache_hit: bool = True
        if self.cache.Get((file.ino, start), True):
            pass
        else:
            if self.ratio != 1:
                sys_start: int = int(start * self.ratio - (1/4096 if start != 0 else 0))
                sys_size: int = int((start + size - 0.00001) * self.ratio) - sys_start + 1
            else:
                sys_start = start
                sys_size = size
            for g in self.page_cache.Read(file, sys_start, sys_size, activate=False):
                yield g
            stats.s.app_cost += self.miss_penalty
            yield self.env.timeout(self.miss_penalty)
            evicteds: list[tuple[tuple[int, int], AppCacheItem]] = self.cache.Put((file.ino, start), size, True)
            cache_hit = False

            # for evicted in evicteds:
            #     # if int(round(evicted[1].size * self.ratio, 1)) == 1:
            #         if self.sys.page_cache.cache.Get(evicted[0], True) is None:
            #             self.sys.page_cache.cache.PutMany([(evicted[0], self.env.now + 20, False, False, True)])
            #         else:
            #             self.sys.page_cache.cache.Ref(evicted[0])
        
        # stats
        if cache_hit:
            stats.s.app_cache_hit_num += 1
        else:
            stats.s.app_cache_miss_num += 1
        # adapter.a.Record(file, start, size, app=True, hit=cache_hit)
