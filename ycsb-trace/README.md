Work around playing with ycsb

* Required: setup ycsb (0.17.0) as the document
* HOWTO use?
    0. `source ./ycsb.env`
    1. Generate a ycsb workload
        * Look at `gen_ycsb_job.py`: the python script contains the function to automatically generate
            the workload configuration that YCSB will use as input
            * The python script will name the workload properly by the configuraed paremeter
    2. Copy the generated workload in *1* into `./workloads` (because the shell script use the directory).
    3. Run the workload, process the results and generate the traces (req-trace/block-trace)
        * Take a look at what the shell scripts do; the scripts have all the steps and commands needed
            * `./gen_block_trace.sh`
            * `./gen_block_trace_contzipf.sh`
            * `./gen_req_trace.sh`
            * `./gen_req_trace_contzipf.sh`
* How to plot the key range distribution?
    * `plot_key_space_access.py`
        * arg1: trace_name (the trace is the block trace/req trace that contains sequence of numbers)
        * arg2: number of bins
