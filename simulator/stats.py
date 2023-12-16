# from cache import LRUCache


class Stats(object):
    def __init__(self) -> None:
        self.total_latency: int = 0

        # sync async stats
        self.page_cache_hit_num: int = 0
        self.page_cache_miss_num: int = 0
        self.sync_ra: int = 0
        self.async_ra: int = 0
        self.sync_pages: int = 0
        self.async_pages: int = 0
        self.sync_num: int = 0
        self.async_num: int = 0

        # ra stats
        self.readahead_pages: int = 0
        self.readahead_hits: int = 0
        self.wasted_pages: int = 0
        self.ra_flagged: int = 0
        self.ra_cleared: int = 0
        self.ra_evicted: int = 0
        self.contextual_sync_length:int = 0
        self.contextual_async_length: int = 0
        self.ra_type_nums: list[int] = list()
        self.ra_type_pages: list[int] = list()
        for _ in range(0, 7):
            self.ra_type_pages.append(0)
            self.ra_type_nums.append(0)

        # page_cache stats
        self.shadow_promoted: int = 0
        self.shadow_demoted: int = 0
        self.active_size: int = 0
        self.inactive_size: int = 0
        self.active_mark: int = 0
        self.inactive_mark: int = 0
        self.activations: int = 0
        self.evictions: int = 0
        self.eviction_triggered: int = 0
        self.num_scanned: int = 0

        # app stat
        self.app_cache_hit_num: int = 0
        self.app_cache_miss_num: int = 0

        # timing stats
        self.system_cost = 0
        self.app_cost = 0

        # calculated values
        self.random_percentage: float = 0
        self.ra_final: int = 0
        self.num_pages: int = 0
        self.app_cache_hit_ratio: float = 0
        self.page_cache_hit_ratio: float = 0

        # exp
        self.first_page_hit_num = 0
        self.first_page_miss_num = 0
        self.second_page_hit_num = 0
        self.second_page_miss_num = 0
        self.one_page_hit_num = 0
        self.one_page_miss_num = 0
        self.first_page_hit_ratio = 0
        self.second_page_hit_ratio = 0
        self.one_page_hit_ratio = 0
    

    def Calculate(self, cache, env) -> None:
        try:
            self.total_latency = env.now
            self.ra_final = self.ra_flagged - self.ra_cleared - self.ra_evicted
            self.num_pages = sum(self.ra_type_pages)
            self.active_size = len(cache.active)
            self.inactive_size = len(cache.inactive)
            self.activations = cache.activation_count
            self.evictions = cache.eviction_count
            self.app_cache_hit_ratio = self.app_cache_hit_num / (self.app_cache_hit_num + self.app_cache_miss_num)
            self.page_cache_hit_ratio = self.page_cache_hit_num / (self.page_cache_hit_num + self.page_cache_miss_num)
            self.random_percentage = self.ra_type_pages[len(self.ra_type_pages) - 1] / (self.sync_ra + self.async_ra)
            self.first_page_hit_ratio = self.first_page_hit_num / (self.first_page_hit_num + self.first_page_miss_num)
            self.second_page_hit_ratio = self.second_page_hit_num / (self.second_page_hit_num + self.second_page_miss_num)
            self.one_page_hit_ratio = self.one_page_hit_num / (self.one_page_hit_num + self.one_page_miss_num)
        except ZeroDivisionError:
            pass

        for _, value in cache.active.items():
            if value.mark:
                self.active_mark += 1
        for _, value in cache.inactive.items():
            if value.mark:
                self.inactive_mark += 1
    

    def ClearCacheStats(self) -> None:
        self.app_cache_hit_num = 0
        self.app_cache_miss_num = 0
        self.page_cache_hit_num = 0
        self.page_cache_miss_num = 0
    

    def App_Ratio(self) -> float:
        if self.app_cache_hit_num + self.app_cache_miss_num == 0:
            return -1
        return self.app_cache_hit_num / (self.app_cache_hit_num + self.app_cache_miss_num)

    
    def Kernel_Ratio(self) -> float:
        if self.page_cache_hit_num + self.page_cache_miss_num == 0:
            return -1
        return self.page_cache_hit_num / (self.page_cache_hit_num + self.page_cache_miss_num)


s = Stats()
