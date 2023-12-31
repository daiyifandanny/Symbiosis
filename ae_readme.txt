Welcome to Symbiosis! We aim for Available and Functional flag 
due to inability to provide access to our machine with Optane device.

./leveldb, ./wiredtiger, and ./rocksdb contains the three modified storage engines used in our paper.
./traces includes all the traces for our experiments.
./simulator is the cache simulator used in Section 3.

The following commands provide instructions on executing main experiments in our paper.
Please run on a Linux machine with Git, Cmake, Python3, and at least 10GB available memory. Ubuntu is preferred.
Root access is required for clearing kernel page cache, for each data point in each experiment.

# Package install for Ubuntu; for other Linux system, please install these packages by yourself
# A new instance on Cloudlab with Ubuntu 20.04 image should work by exactly following the instructions below.
sudo apt update
sudo apt install systemtap-sdt-dev zstd libzstd-dev libsnappy-dev cmake python3-pip
pip3 install numpy simpy

# Preparation
git clone https://github.com/daiyifandanny/Symbiosis.git
cd Symbiosis/leveldb
mkdir build
cd build
cmake ..
make -j
./db_bench --benchmarks=fillseq --db=leveldb

# Experiments in Section 5.1.1, results will be in ae_static/
python3 ../../scripts/ae_eval_static.py

# Experiments in Section 5.2.2, results will be in ae_dynamic_output/ and ae_dynamic_latency
python3 ../../scripts/ae_eval_dynamic.py

# Experiments in Section 5.3, results will be in ae_final/
python3 ../../scripts/ae_eval_final.py

# Simulations in Section 3, results will be in ae_simulator/
cd ../../simulator
python3 ../scripts/ae_simulator.py

# All experiments and simulations may take hours. 
# Feel free to Ctrl+C when some results are produced and executability is shown
