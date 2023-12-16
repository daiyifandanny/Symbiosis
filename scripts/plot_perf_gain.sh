#! /bin/bash

# Note: I think 37 is quite good.
python plot_perf_gain.py ./results_SET1_SET2_perf_gain.csv 0.1,0.3,0.5,0.7,1.0
mv ./sim_best_size.eps sim_best_size_37.eps
python plot_perf_gain.py ./results_SET1_SET2_perf_gain.csv 0.1,0.1,0.5,0.9,1.0
mv ./sim_best_size.eps sim_best_size_19.eps
python plot_perf_gain.py ./results_SET1_SET2_perf_gain.csv 0.1,0.2,0.5,0.8,1.0
mv ./sim_best_size.eps sim_best_size_28.eps
python plot_perf_gain.py ./results_SET1_SET2_perf_gain.csv 0.1,0.4,0.5,0.6,1.0
mv ./sim_best_size.eps sim_best_size_46.eps

