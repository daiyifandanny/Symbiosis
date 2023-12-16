#! /bin/bash

# uniform random
#python plot_mem_ratio_lat.py ./results_all.csv 0.5 50 0 k
#python plot_mem_ratio_lat.py ./results_all.csv 0.5 50 0 a

# skewed
#python plot_mem_ratio_lat.py ./results_all.csv 0.5 50 0 k
#python plot_mem_ratio_lat.py ./results_all.csv 0.5 50 0 a

for COMPRESS_RATIO in 0.1 0.2 0.3 0.4 0.5 0.6 0.7 0.8 0.9 1
do
    for MISS_COST in 10 50 100
    do
        for JOB in 0 1
        do
            python plot_mem_ratio_lat.py ./results_all.csv $COMPRESS_RATIO $MISS_COST $JOB k
            python plot_mem_ratio_lat.py ./results_all.csv $COMPRESS_RATIO $MISS_COST $JOB a
        done
    done
done
