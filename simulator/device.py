from tokenize import single_quoted
import simpy


class BlockDevice(object):
    def __init__(self, env: simpy.Environment, seq_latency: int, rand_latency: int) -> None:
        self.env: simpy.Environment = env
        self.seq_single_latency: int = seq_latency
        self.rand_single_latency: int = rand_latency
        self.last: int = None
    
    
    def Read(self, target: int, length: int):
        ret = list()
        single_latency = self.seq_single_latency if self.last is not None and target == self.last + 1 else self.rand_single_latency
        self.last = target + length - 1;
        total_latency: int = min(length, 16) * single_latency
        first_latency: int = single_latency
        for i in range(0, length):
            if i < 4:
                first_latency += 10
            elif i < 8:
                first_latency += 15
            else:
                first_latency += 20

        for i in range(0, length):
            # num_portion: int = min(length, 16) - 1
            # this_portion: int = min(i + 1, 16) - 1
            # arrival_time: int = self.env.now + first_latency
            # if num_portion != 0:
            #     arrival_time += (total_latency - first_latency) * this_portion // num_portion
            # ret.append(arrival_time)
            ret.append(self.env.now + first_latency)
        return ret
