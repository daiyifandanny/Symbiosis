from collections import OrderedDict
import typing

from numpy import true_divide


class CacheItem(object):
    def __init__(self) -> None:
        pass


class LRUCache(object):
    def __init__(self, capacity: int) -> None:
        self.cache: typing.OrderedDict[tuple[int, int], CacheItem] = OrderedDict()
        self.capacity: int = capacity
    

    def Get(self, key: tuple[int, int], reference: bool) -> bool:
        if key in self.cache:
            if reference:
                self.cache.pop(key)
                self.cache[key] = CacheItem()
            return True
        return False


    def Put(self, key: tuple[int, int]) -> None:
        if len(self.cache) + 1 >= self.capacity:
            self.Evict()
        self.cache[key] = CacheItem()


    def Evict(self) -> None:
        self.cache.popitem(last=False)
