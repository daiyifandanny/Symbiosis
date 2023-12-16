#! /bin/bash

set -e

function run_one_hotspot_pair() {
    HOTSPOT_KEY_PCT=$1
    HOTSPOT_OP_PCT=$2
    for MAX_KEY in 10 20 25 40 50 80
    do
        JOB_NAME="Job_hotspot-NumAccess_10M-Maxkey_${MAX_KEY}M-HotspotKeyPct-${HOTSPOT_KEY_PCT}_HotspotOpPct-${HOTSPOT_OP_PCT}"
        echo $JOB_NAME
        OUT_NAME="$JOB_NAME.out"
        $YCSB_BIN run basic -P workloads/"ro-$JOB_NAME" > "$OUT_NAME"
        python ./gen_req_trace.py ${OUT_NAME} "${MAX_KEY}000000" 1g 0
        REQ_TRACE_NAME="$JOB_NAME.out.req.trace"
        ##python ./plot_key_space_access.py $REQ_TRACE_NAME 1000
        ##python from_sczipf_to_contzipf.py ${REQ_TRACE_NAME} "${MAX_KEY}000000" 1g 0 0.1,0.9
        ls ${JOB_NAME}*
        mv ${JOB_NAME}*  ./req-trace-hotspot/
        #mv Job_hotspot* ./req-trace-hotspot/
    done
}

run_one_hotspot_pair 10 90
run_one_hotspot_pair 20 80
run_one_hotspot_pair 30 70



