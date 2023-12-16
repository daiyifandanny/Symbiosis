from enum import Enum
import sys
import copy
import stats
import numpy
import system
import application


class AdapterState(Enum):
    STABLE = 0
    LEFT = 1
    RIGHT = 2
    JUMP = 3
    HEAT = 4
    SEARCH = 5


class JumpState(Enum):
    LEFT = 0
    RIGHT = 1


class CacheStat(object):
    def __init__(self, acs, kcs, acmc, kcmc, e) -> None:
        self.app_cache_size: int = acs
        self.kernel_cache_size: int = kcs
        self.app_cache_miss_cost: int = acmc
        self.kernel_cache_miss_cost: int = kcmc

        self.app_cache_num: int = 0
        self.app_cache_hit: int = 0
        self.kernel_cache_num: int = 0
        self.kernel_cache_hit: int = 0
        self.expectation: float = e
    

    def Record(self, app: bool, hit: bool) ->None:
        if app:
            self.app_cache_num += 1
            if hit:
                self.app_cache_hit += 1
        else:
            self.kernel_cache_num += 1
            if hit:
                self.kernel_cache_hit += 1

    
    def Clear(self) -> None:
        self.app_cache_num = 0
        self.app_cache_hit = 0
        self.kernel_cache_num = 0
        self.kernel_cache_hit = 0
        self.expectation = None
    

    def Calculate(self) -> None:
        app_cache_ratio : float = self.app_cache_hit / self.app_cache_num
        kernel_cache_ratio : float = self.kernel_cache_hit / self.kernel_cache_num if self.kernel_cache_num != 0 else 1
        self.expectation = (1 - app_cache_ratio) * (self.app_cache_miss_cost + (1 - kernel_cache_ratio) * self.kernel_cache_miss_cost)

    

class Adapter(object):
    def __init__(self) -> None:
        self.period_length : int = 20000
        self.stable_tolerance : float = 0.9
        self.jump_tolerance : float = 0.9
        self.delta_ratio : float = 0.1
        self.delta_tolerance : float = 0.98
        self.debug_file = open("adapter_output.txt", "w")

        self.app_cache_miss_cost : int = 0
        self.kernel_cache_miss_cost : int = 0
        self.total_size : int = 0
        self.app_cache : application.AppCache = None
        self.kernel_cache: system.Kernel = None

        self.app_cache_filled : bool = True
        self.kernel_cache_filled : bool = True
        self.delta_moved : bool = False
        self.jumped : bool = False
        self.jump_state : JumpState = JumpState.RIGHT
        self.state : AdapterState = AdapterState.STABLE

        self.counter : int = 0
        self.app_cache_hit : int = 0
        self.kernel_cache_hit : int = 0
        self.kernel_cache_num : int = 0
        self.current_best : CacheStat = CacheStat(0, 0, 0, 0, 0)
        self.before_jump_best : CacheStat = CacheStat(0, 0, 0, 0, sys.maxsize)

        self.global_counter : int = 0
    

    def FillParameter(self, app_cache_miss_cost, kernel_cache_miss_cost, total_size, app_cache, kernel_cache) -> None:
        self.app_cache_miss_cost = app_cache_miss_cost
        self.kernel_cache_miss_cost = kernel_cache_miss_cost
        self.total_size = total_size
        self.app_cache = app_cache
        self.kernel_cache = kernel_cache
    
    
    def Filled(self) -> bool:
        return self.app_cache_filled and self.kernel_cache_filled
    

    def CacheFilled(self, app : bool) -> None:
        if app:
            self.app_cache_filled = True
        else:
            self.kernel_cache_filled = True

    
    def ClearCurrent(self) -> None:
        self.counter = 0
        self.app_cache_hit = 0
        self.kernel_cache_hit = 0
        self.kernel_cache_num = 0

    
    def CalculateCurrent(self) -> CacheStat:
        app_cache_ratio : float = self.app_cache_hit / self.counter
        kernel_cache_ratio : float = self.kernel_cache_hit / self.kernel_cache_num if self.kernel_cache_num != 0 else 1
        expectation : float = (1 - app_cache_ratio) * (self.app_cache_miss_cost + (1 - kernel_cache_ratio) * self.kernel_cache_miss_cost)
        return CacheStat(self.app_cache.capacity, self.kernel_cache.capacity, app_cache_ratio, kernel_cache_ratio, expectation)
    

    def CalculateEstimation(self) -> CacheStat:
        working_size_decompressed : int = int(self.current_best.app_cache_size / self.current_best.app_cache_ratio)
        working_size_compressed : int = int(working_size_decompressed * self.app_cache.ratio)
        
        jump_app_cache_size : int = 0
        jump_kernel_cache_size : int = 0
        # invalid : bool = False
        if self.jump_state == JumpState.RIGHT:
            jump_kernel_cache_size = min(working_size_compressed, self.total_size)
            jump_app_cache_size = self.total_size - jump_kernel_cache_size
            if self.kernel_cache.capacity >= jump_kernel_cache_size:
                assert False
        else:
            jump_app_cache_size = self.total_size - 256
            jump_kernel_cache_size = 256
            if self.app_cache.capacity >= jump_app_cache_size:
                assert False
        
        app_cache_ratio : float = jump_app_cache_size / working_size_decompressed
        kernel_cache_ratio : float = jump_kernel_cache_size / working_size_compressed
        if app_cache_ratio > 1 or kernel_cache_ratio > 1:
            assert False
        expectation : float = (1 - app_cache_ratio) * (self.app_cache_miss_cost + (1 - kernel_cache_ratio) * self.kernel_cache_miss_cost)
        return CacheStat(jump_app_cache_size, jump_kernel_cache_size, app_cache_ratio, kernel_cache_ratio, expectation)


    def Record(self, app : bool, hit : bool) -> None:
        if app:
            self.global_counter += 1
        if not self.Filled():
            return

        if app:
            if hit:
                self.app_cache_hit += 1
            self.counter += 1
            if self.counter >= self.period_length:
                self.StateFunction()
        else:
            if hit:
                self.kernel_cache_hit += 1
            self.kernel_cache_num += 1

    
    def StateFunction(self) -> None:
        current_stat : CacheStat = self.CalculateCurrent()
        self.ClearCurrent()
        state_changed : bool = False

        print("{} {} {:.2f} {}".format(self.global_counter, self.kernel_cache.capacity, current_stat.expectation, self.state), file=self.debug_file)

        if self.state == AdapterState.STABLE:
            if self.current_best.expectation / current_stat.expectation < self.stable_tolerance:
                # current best is outdated, record new (worse) result
                self.current_best = current_stat
                self.state = AdapterState.LEFT
                state_changed = True
            else:
                return
        
        if self.state == AdapterState.LEFT:
            if current_stat.expectation / self.current_best.expectation < self.delta_tolerance or state_changed:
                # start moving
                if not state_changed:
                    self.delta_moved = True
                    self.current_best = current_stat
                if self.app_cache.capacity != 0:
                    # keep moving
                    delta : int = min(int(self.total_size * self.delta_ratio), self.app_cache.capacity)
                    self.app_cache.ChangeSize(-delta, True)
                    self.kernel_cache.ChangeSize(delta, True)
                    self.kernel_cache_filled = False
                    return

            # stop moving, restore best case
            if self.current_best.app_cache_size != current_stat.app_cache_size:
                self.app_cache.ChangeSize(self.current_best.app_cache_size, False)
                self.kernel_cache.ChangeSize(self.current_best.kernel_cache_size, False)
                self.app_cache_filled = False

            if self.delta_moved:
                self.state = AdapterState.JUMP
            else:
                self.state = AdapterState.RIGHT
            self.delta_moved = False
            state_changed = True
        
        if self.state == AdapterState.RIGHT:
            if current_stat.expectation / self.current_best.expectation < self.delta_tolerance or state_changed:
                # start moving
                if not state_changed:
                    self.current_best = current_stat
                if self.kernel_cache.capacity > 256:
                    # keep moving
                    delta : int = min(int(self.total_size * self.delta_ratio), self.kernel_cache.capacity - 256)
                    self.app_cache.ChangeSize(delta, True)
                    self.kernel_cache.ChangeSize(-delta, True)
                    self.app_cache_filled = False
                    return
            
            # stop moving, restore best case
            if self.current_best.app_cache_size != current_stat.app_cache_size:
                self.app_cache.ChangeSize(self.current_best.app_cache_size, False)
                self.kernel_cache.ChangeSize(self.current_best.kernel_cache_size, False)
                self.kernel_cache_filled = False

            self.state = AdapterState.JUMP
            state_changed = True
        
        if self.state == AdapterState.JUMP:
            # estimate cost on the other side
            if not self.jumped:
                estimated_stat : CacheStat = self.CalculateEstimation()
                if estimated_stat.expectation / self.current_best.expectation < self.jump_tolerance:
                    # do jump
                    self.before_jump_best = self.current_best
                    self.current_best = CacheStat(0, 0, 0, 0, 0)
                    self.state = AdapterState.STABLE
                    self.jumped = True
                    self.app_cache.ChangeSize(estimated_stat.app_cache_size, False)
                    self.kernel_cache.ChangeSize(estimated_stat.kernel_cache_size, False)
                    if self.jump_state == JumpState.RIGHT:
                        self.kernel_cache_filled = False
                        self.jump_state = JumpState.LEFT
                    else:
                        self.app_cache_filled = False
                        self.jump_state = JumpState.RIGHT
                    return
            
            # no jump, wrap up to be stable
            if self.jumped and self.before_jump_best.expectation / self.current_best.expectation < self.jump_tolerance:
                assert False
            self.state = AdapterState.STABLE
            self.jumped = False
            self.before_jump_best = CacheStat(0, 0, 0, 0, sys.maxsize)


class Simulator(object):
    def __init__(self, num_searches: int, total_size: int, app_cache_miss_cost: int, kernel_cache_miss_cost: int, max_pages: int, max_readahead: int, ratio: float) -> None:
        self.num_searches: int = num_searches
        self.total_size: int = total_size
        self.app_cache_miss_cost: int = app_cache_miss_cost
        self.kernel_cache_miss_cost: int = kernel_cache_miss_cost
        self.max_pages: int = max_pages
        self.max_readahead: int = max_readahead
        self.ratio: float = ratio

        self.stats: list[CacheStat] = list()
        self.apps: list[application.Application] = list()
        # numpy.random.seed(811)
        # list1 = numpy.random.permutation(max_pages)
        # numpy.random.seed(210)
        # list2 = numpy.random.permutation(max_pages)
        # for i in range(0, num_searches + 1):
        #     kernel_cache_size = 256 if i == 0 else total_size * i // num_searches
        #     page_cache = system.PageCache(None, None, kernel_cache_size, None, max_readahead)
        #     app = application.Application(None, None, total_size - kernel_cache_size, ratio, None, page_cache)
            
        #     for i in list1:
        #         ret = page_cache.cache.PutMany([((0, i), 0, False, False, False)])
        #         if ret != 0:
        #             break
        #     for i in list2:
        #         ret = app.cache.Put((0, i), 1)
        #         if len(ret) != 0:
        #             break
                
            # self.apps.append(app)
            # self.stats.append(CacheStat(total_size - kernel_cache_size, kernel_cache_size, app_cache_miss_cost, kernel_cache_miss_cost, None))


    def Simulate(self, file, start, size) -> None:
        for i in range(0, self.num_searches + 1):
            app_hit, kernel_hit = self.apps[i].Simulate(file, start, size)
            self.stats[i].Record(True, app_hit)
            if not app_hit:
                self.stats[i].Record(False, kernel_hit)


    def BestStat(self) -> CacheStat:
        best_index = -1
        best_expectation = sys.maxsize
        for i in range(0, self.num_searches + 1):
            self.stats[i].Calculate()
            if self.stats[i].expectation < best_expectation:
                best_index = i
                best_expectation = self.stats[i].expectation
        return copy.copy(self.stats[best_index])

    
    def ClearStats(self) -> None:
        for i in range(0, self.num_searches + 1):
            self.stats[i].Clear()
    

    def Clear(self) -> None:
        self.__init__(self.num_searches, self.total_size, self.app_cache_miss_cost, self.kernel_cache_miss_cost, self.max_pages, self.max_readahead, self.ratio)
        

class Adapter2(object):
    def __init__(self) -> None:
        self.period_length : int = 20000
        self.stable_tolerance : float = 0.9
        self.jump_tolerance : float = 0.9
        self.debug_file = open("adapter_output.txt", "w")

        self.app_cache_miss_cost : int = 0
        self.kernel_cache_miss_cost : int = 0
        self.total_size : int = 0
        self.app_cache: application.AppCache  = None
        self.kernel_cache: system.Kernel = None

        self.app_cache_filled : bool = True
        self.kernel_cache_filled : bool = True
        self.state : AdapterState = AdapterState.STABLE
        self.simulator: Simulator = None

        self.current_stat: CacheStat = None
        self.best_stat: CacheStat = CacheStat(0, 0, 0, 0, 0)

        self.global_counter : int = 0
    

    def FillParameter(self, app_cache_miss_cost, kernel_cache_miss_cost, total_size, app_cache, kernel_cache, max_pages) -> None:
        self.app_cache_miss_cost = app_cache_miss_cost
        self.kernel_cache_miss_cost = kernel_cache_miss_cost
        self.total_size = total_size
        self.app_cache = app_cache
        self.kernel_cache = kernel_cache.cache
        self.simulator = Simulator(10, total_size, app_cache_miss_cost, kernel_cache_miss_cost, max_pages, kernel_cache.max_readahead, self.app_cache.ratio)
        self.current_stat = CacheStat(self.app_cache.capacity, self.kernel_cache.capacity, self.app_cache_miss_cost, self.kernel_cache_miss_cost, None)
    
    
    def Filled(self) -> bool:
        return self.app_cache_filled and self.kernel_cache_filled
    

    def CacheFilled(self, app : bool) -> None:
        prev_filled: bool = self.Filled()

        if app:
            self.app_cache_filled = True
        else:
            self.kernel_cache_filled = True
        
        if not prev_filled and self.Filled():
            self.ClearCurrent()
    

    def ClearCurrent(self) -> None:
        self.current_stat.Clear()


    def Record(self, file, start, size, app : bool, hit : bool) -> None:
        return
        self.current_stat.Record(app, hit)

        if app:
            self.global_counter += 1
            
            if self.state != AdapterState.STABLE:
                self.simulator.Simulate(file, start, size)

            if self.current_stat.app_cache_num >= self.period_length:
                self.StateFunction()

    
    def StateFunction(self) -> None:
        self.current_stat.Calculate()
        current_stat: CacheStat = copy.copy(self.current_stat)
        self.ClearCurrent()

        print("{} {} {:.2f} {}".format(self.global_counter, self.kernel_cache.capacity, current_stat.expectation, self.state), file=self.debug_file)
        
        # return
        if not self.Filled():
            return

        if self.state == AdapterState.STABLE:
            if self.best_stat.expectation is None:
                self.best_stat = current_stat
                return
            
            if self.best_stat.expectation / current_stat.expectation < self.stable_tolerance:
                # current best is outdated, record new (worse) result
                self.best_stat = current_stat
                self.state = AdapterState.HEAT
                self.simulator.Clear()
        
        elif self.state == AdapterState.HEAT:
            self.state = AdapterState.SEARCH
            self.simulator.ClearStats()

        elif self.state == AdapterState.SEARCH:
            self.state = AdapterState.STABLE
            simulated_best_stat = self.simulator.BestStat()
            if simulated_best_stat.expectation / self.best_stat.expectation < self.jump_tolerance:
                # do jump
                self.best_stat = simulated_best_stat
                self.app_cache.ChangeSize(simulated_best_stat.app_cache_size, False)
                self.kernel_cache.ChangeSize(simulated_best_stat.kernel_cache_size, False)
                self.app_cache_filled = False
                self.kernel_cache_filled = False


a = Adapter2()

