from math import sqrt
from collections import OrderedDict
import typing
import simpy
import stats
import adapter
import random


class CacheItem:
    def __init__(self) -> None:
        self.ref_count: int = 0
        self.readahead: bool = False
        self.arrival = 0
        self.mark: bool = False
        self.referenced = False


class PageCache:
    def __init__(self, capacity: int, env: simpy.Environment) -> None:
        self.active = OrderedDict()
        self.inactive = OrderedDict()
        self.shadow_entries = OrderedDict()
        self.capacity: int = int(capacity * 1)
        self.min_eviction = 64
        self.shift = 4096
        self.eviction_count = 0
        self.activation_count = 0
        self.env: simpy.Environment = env
        self.eviction_cost = 150

        # stats
        self.debug_output = open("page_cache_debug.txt", "w")
        self.active_marks = 0
        self.inactive_marks = 0
        self.current_ra_type = 0

    
    def ChangeSize(self, size : int, delta : bool) -> None:
        if self.capacity == 0:
            return
        
        self.shift = 4096

        if delta:
            self.capacity += size
        else:
            self.capacity = size
        
        if self.capacity < 256:
            assert False
        
        while self.Size() >= self.capacity:
            while len(self.inactive) < len(self.active):
                pair = self.active.popitem(last=False)
                self.InsertInactive(pair[0], pair[1])
            self.Evict()
        
        while len(self.shadow_entries) >= self.capacity:
            self.shadow_entries.popitem(last=False)
        
        self.shift = 4096
        
    
    def Size(self) -> int:
        return len(self.active) + len(self.inactive)

    
    def RefaultCounter(self) -> int:
        return int((self.eviction_count + self.activation_count) * 1)


    def GetScanCount(self, target: typing.OrderedDict) -> int:
        amount: int = len(target) // self.shift
        while amount < self.min_eviction:
            self.shift //= 2
            amount = len(target) // self.shift
        # print(len(target), amount)
        # return min(amount, 16384)
        return amount


    def InsertActive(self, key, value: CacheItem) -> None:
        assert key not in self.active
        assert key not in self.inactive
        self.activation_count += 1
        self.active[key] = value
    

    def InsertInactive(self, key, value: CacheItem) -> None:
        assert key not in self.inactive
        assert key not in self.active
        self.inactive[key] = value
        
        
    def Ref(self, key) -> None:
        # return
        if key in self.active:
            item: CacheItem = self.active[key]
            item.ref_count += 1
            item.referenced = True
        elif key in self.inactive:
            item: CacheItem = self.inactive[key]
            item.ref_count += 1
            if item.referenced:
                item.referenced = False
                self.inactive.pop(key)
                self.InsertActive(key, item)
            else:
                item.referenced = True

    
    def ShrinkActive(self) -> int:
        amount: int = min(self.GetScanCount(self.active), len(self.active))
        for _ in range(0, amount):
            pair = self.active.popitem(last=False)
            self.InsertInactive(pair[0], pair[1])
        return amount
    
    
    def Evict(self) -> int:
        adapter.a.CacheFilled(app=False)
        stats.s.eviction_triggered += 1
        ratio: float = 1
        num_scanned: int = 0
        gb: int = self.capacity * 4096 // (1024 * 1024 * 1024)
        if gb >= 1:
            ratio = sqrt(gb * 10)
        if len(self.inactive) * ratio < len(self.active):
            self.ShrinkActive()
        if len(self.inactive) < self.min_eviction:
            assert False

        # self.shift = 4096
        inactive_scan_count: int = self.GetScanCount(self.inactive)
        for _ in range(0, inactive_scan_count):
            pair = self.inactive.popitem(last=False)
            # evicted and do shadow entries
            if True:
                # assert pair[0] not in self.shadow_entries
                self.shadow_entries[pair[0]] = self.RefaultCounter() + len(self.active)
                # if len(self.shadow_entries) // 56 > int(self.max_capacity * 0.018):
                if len(self.shadow_entries) >= self.capacity:
                    self.shadow_entries.popitem(last=False)
            self.eviction_count += 1


            # stat
            if pair[1].ref_count == 0:
                stats.s.wasted_pages += 1
            stats.s.ra_evicted += 1 if pair[1].mark else 0
        num_scanned += inactive_scan_count
        stats.s.num_scanned += num_scanned
        return num_scanned

    
    def Get(self, key, reference: bool = True, active: bool = False) -> CacheItem:
        if self.capacity == 0:
            return None

        item: CacheItem = None
        if key in self.active:
            item = self.active[key]
        elif not active and key in self.inactive:
            item = self.inactive[key]
        
        if reference and item is not None:
            self.Ref(key)
        return item
        
    
    def Put(self, key, arrival: int, reference: bool, mark: bool, activate: bool) -> None:
        item = CacheItem()
        item.arrival = arrival
        item.mark = mark
        item.referenced = False
        item.ref_count = 0
        if reference:
            item.readahead = False
        else:
            item.readahead = True
        
        # refault distance calculation
        if key in self.shadow_entries:
            if self.RefaultCounter() <= self.shadow_entries.pop(key):
                self.InsertActive(key, item)
                stats.s.shadow_promoted += 1
            else:
                self.InsertInactive(key, item)
                stats.s.shadow_demoted += 1
        elif activate:
            self.InsertActive(key, item)
        else:
            self.InsertInactive(key, item)
        # self.InsertActive(key, item)
        
        # debug
        stats.s.ra_flagged += 1 if mark else 0
        print("{}".format(key[1]), file=self.debug_output)


    def PutMany(self, args) -> bool:
        if self.capacity == 0:
            return

        eviction_cost: int = 0
        num_scanned = 0
        if self.Size() + len(args) >= self.capacity:
            num_scanned = self.Evict()
            # eviction_cost += num_scanned * 4

        for arg in args:
            self.Put(arg[0], arg[1] + eviction_cost, arg[2], arg[3], arg[4])
        
        return num_scanned
