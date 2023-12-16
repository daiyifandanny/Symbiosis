#! /bin/bash

set -e


for MEM_RATIO in 0.4 0.5 0.6 0.7 0.8
do
    for COMPRESS_RATIO in 0.4 0.5 0.6
    do
        for JOB in 1 #0 1
        do
            echo "==> $MEM_RATIO $COMPRESS_RATIO $JOB"
            python plot_miss_cost_lat.py results_SET3_bothjobs.csv $MEM_RATIO $COMPRESS_RATIO $JOB k
            python plot_miss_cost_lat.py results_SET3_bothjobs.csv $MEM_RATIO $COMPRESS_RATIO $JOB a
        done
    done
done


exit

for MEM_RATIO in 0.4 0.5 0.6 0.7 0.8
do
    for COMPRESS_RATIO in 0.4 0.5 0.6
    do
        for JOB in 0 #1
        do
            echo "==> $MEM_RATIO $COMPRESS_RATIO $JOB"
            python plot_miss_cost_lat.py results_SET3.csv $MEM_RATIO $COMPRESS_RATIO $JOB k
            python plot_miss_cost_lat.py results_SET3.csv $MEM_RATIO $COMPRESS_RATIO $JOB a
        done
    done
done

