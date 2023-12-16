import subprocess
import signal
import time
import argparse


mongo_base_path = "/home/yifan/research/cache/mongo"
server_path = mongo_base_path + "/server/build/install/bin/mongod"
client_path = mongo_base_path + "/client/simple_read"

parser = argparse.ArgumentParser()
parser.add_argument("-w", "--write", required=False, help="is write", default=False, action="store_true")
parser.add_argument("-r", "--random", required=False, help="is random", default=False, action="store_true")
parser.add_argument("-m", "--mmap", required=False, help="is mmap", default=False, action="store_true")
parser.add_argument("--cache_size", required=False, type=int, help="in GB")
args = parser.parse_args()


# start server
server_output = open("server.out", "w")
server_command = "cgexec -g memory:5 " + server_path + \
                    " --port 21021 --dbpath /nvme/mongo --wiredTigerCollectionBlockCompressor none --nojournal" + \
                    " --wiredTigerCacheSizeGB 0.01"
print(server_command)
server_process = subprocess.Popen(server_command, shell=True, stdout=server_output);
time.sleep(5);

# start workload
worker_command = client_path
if args.write:
    worker_command += " -w"
if args.random:
    worker_command += " -r"
if args.mmap:
    worker_command += " -m"
print(worker_command)
subprocess.run(worker_command, shell=True)

# kill server
time.sleep(5)
subprocess.run("pkill -2 mongod", shell=True)
