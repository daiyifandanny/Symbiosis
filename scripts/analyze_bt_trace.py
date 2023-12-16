import sys


num_sets = 6


dicts : list[dict[int, int]] = list()
for _ in range(0, num_sets):
    dicts.append(dict())

with open(sys.argv[1], "r") as trace_file:
    lines = trace_file.readlines()
    for index, line in enumerate(lines):
        # if index > 8000:
        #     break
        dictid = index % num_sets
        dicts[dictid][int(line.split()[0])] = int(line.split()[1])

for index, d in enumerate(dicts):
    l = list(d)
    l.sort()
    sum: int = 0
    for item in d.items():
        sum += item[1]
    print("Set {} Num {} Size {} Range {} ~ {}".format(index, len(l), sum, l[0], l[len(l) - 1]))
