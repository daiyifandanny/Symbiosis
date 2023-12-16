#! /bin/bash

set -e

function run_one_job() {
    MAX_KEY=$1
    HOTSPOT_KEY_PCT=$2
    HOTSPOT_OP_PCT=$3
    DISK_DATA_BYTE=$4

    echo "MAX_KEY: $MAX_KEY"
    echo "HOTSPOT_KEY_PCT: $HOTSPOT_KEY_PCT"
    echo "HOTSPOT_OP_PCT: $HOTSPOT_OP_PCT"
    echo "DISK_DATA_BYTE: $DISK_DATA_BYTE"

    JOB_NAME="Job_sczipf-NumAccess_11M-Maxkey_${MAX_KEY}M-HotspotKeyPct-${HOTSPOT_KEY_PCT}_HotspotOpPct-${HOTSPOT_OP_PCT}"
    echo $JOB_NAME

    OUT_NAME="$JOB_NAME.out"
    $YCSB_BIN run basic -P workloads/"ro-$JOB_NAME" > "$OUT_NAME"
    ##python ./gen_req_trace.py ${OUT_NAME} 0 10000000 1g 1
    python ./gen_req_trace.py ${OUT_NAME} "${MAX_KEY}000000" ${DISK_DATA_BYTE} 1
    REQ_TRACE_NAME="$JOB_NAME.out.req.trace"
    python ./plot_key_space_access.py $REQ_TRACE_NAME 1000
    python from_sczipf_to_contzipf.py ${REQ_TRACE_NAME} "${MAX_KEY}000000" 1g 1 0.1,0.9
    ls ${JOB_NAME}*
    mv ${JOB_NAME}*  ./block-trace-contzipf
    mv Job_contzipf* ./block-trace-contzipf
}


run_one_job 10 10 90 1g
run_one_job 10 20 80 1g
run_one_job 50 10 90 5g
run_one_job 50 20 80 5g


