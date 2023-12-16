#! /bin/bash

set -e

function run_one_hotspot_pair() {
    REQ_DIST=$1
    HOTSPOT_KEY_PCT=$2
    HOTSPOT_OP_PCT=$3
    #for MAX_KEY in 10 20 25 40 50 80
    for RATIO in 0.2 0.4 0.6 0.8 1
    do
        #JOB_NAME="Job_hotspot-NumAccess_10M-Maxkey_${MAX_KEY}M-HotspotKeyPct-${HOTSPOT_KEY_PCT}_HotspotOpPct-${HOTSPOT_OP_PCT}"
        JOB_NAME="${REQ_DIST}${HOTSPOT_OP_PCT}_10M_${RATIO}"
        echo $JOB_NAME
        OUT_NAME="$JOB_NAME.out"
        $YCSB_BIN run basic -P workloads/"$JOB_NAME" > "$OUT_NAME"
        python ./gen_req_trace.py ${OUT_NAME} "${MAX_KEY}000000" 1g 0
        REQ_TRACE_NAME="${JOB_NAME}_req.trace"
        ##python ./plot_key_space_access.py $REQ_TRACE_NAME 1000
        ##python from_sczipf_to_contzipf.py ${REQ_TRACE_NAME} "${MAX_KEY}000000" 1g 0 0.1,0.9
        ls ${JOB_NAME}*
        mv ${JOB_NAME}*  ./swot-req-trace/
        #mv Job_hotspot* ./req-trace-hotspot/
    done
}

run_one_hotspot_pair uniform 10 90
run_one_hotspot_pair uniform 20 80
run_one_hotspot_pair uniform 30 70

run_one_hotspot_pair hotspot 10 90
run_one_hotspot_pair hotspot 20 80
run_one_hotspot_pair hotspot 30 70

run_one_hotspot_pair zipfian 10 90
run_one_hotspot_pair zipfian 20 80
run_one_hotspot_pair zipfian 30 70
