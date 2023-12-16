import pysqlite3
import subprocess
import time
import argparse
import fastrand


value = 'a' * 80
num_entries = 9000000
num_reads = num_entries // 20


def progress_report(progress, total):
    if progress % (total / 100) == 0:
        print("{} % done".format(progress / (total / 100)), end="\r", flush=True)    


parser = argparse.ArgumentParser()
parser.add_argument("--benchmark", required=True, type=str, help="benchmark name")
parser.add_argument("--page_size", required=True, type=int, help="in Byte")
parser.add_argument("--cache_size", required=True, type=int, help="in KB")
args = parser.parse_args()


preparation_command = "sync; echo 3 | sudo tee /proc/sys/vm/drop_caches; sudo fstrim -av"
subprocess.run(preparation_command, shell=True)

print("started")

fill = "fill" in args.benchmark
if fill:
    subprocess.run("rm /nvme/sqlite/test.db", shell=True)
connection = pysqlite3.connect("/nvme/sqlite/test.db")
connection.isolation_level = None
cursor = connection.cursor()
cursor.execute("PRAGMA page_size={}".format(args.page_size))
cursor.execute("PRAGMA cache_size=-{}".format(args.cache_size))

if fill:
    cursor.execute("CREATE TABLE kv (key integer, value text)")
    cursor.execute("CREATE INDEX ikv ON kv(key)")

print("prepared")

start = time.time()
cursor.execute("begin")

if args.benchmark == "fillseq":
    for key in range(num_entries):
        cursor.execute("INSERT INTO kv VALUES ('{}', '{}')".format(key, value))
        progress_report(key, num_entries)

elif args.benchmark == "fillrandom":
    for counter in range(num_entries):
        key = fastrand.pcg32bounded(num_entries)
        cursor.execute("INSERT INTO kv VALUES ('{}', '{}')".format(key, value))
        progress_report(counter, num_entries)

elif args.benchmark == "readseq":
    for key in range(num_reads):
        cursor.execute("SELECT * FROM kv where key = '{}'".format(key))
        temp = cursor.fetchall()
        if key == 0:
            print(temp)
        progress_report(key, num_reads)

elif args.benchmark == "readrandom":
    for counter in range(num_reads):
        key = fastrand.pcg32bounded(num_entries)
        cursor.execute("SELECT * FROM kv where key = '{}'".format(key))
        temp = cursor.fetchall()
        if counter == 0:
            print(temp)
        progress_report(counter, num_reads)

else:
    assert False


print("done")

cursor.execute("commit")
end = time.time()

print("committed")

connection.close()

print("closed")

print("TP : {} op/s".format((num_entries if fill else num_reads) / (end - start)))
