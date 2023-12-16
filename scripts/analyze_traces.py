import sys


key_max = int(10000000 * float(sys.argv[2]))

buckets = list()
for i in range(0, 100, 1):
    buckets.append(0)

with open(sys.argv[1], "r") as trace_file:
	lines = trace_file.readlines()
	for line in lines:
		try:
			key = int(line)
			buckets[int(key * 100 / key_max)] += 1
		except:
			continue

# sorted_buckets = sorted(buckets, reverse=True)

# # while sorted_buckets[-1] == 0:
# #     sorted_buckets.pop()

# sum_10 = sum(sorted_buckets[:int(len(sorted_buckets) / 10)])

# print(sum_10)
print(buckets)
