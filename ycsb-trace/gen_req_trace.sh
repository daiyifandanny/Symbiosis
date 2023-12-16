#! /bin/bash


for MAX_KEY in 10 20 25 40 50 80
do
    JOB_NAME="Job_sczipf-NumAccess_10M-Maxkey_${MAX_KEY}M-HotspotKeyPct-20_HotspotOpPct-80"
    echo $JOB_NAME
    OUT_NAME="$JOB_NAME.out"
    $YCSB_BIN run basic -P workloads/"ro-$JOB_NAME" > "$OUT_NAME"
    ##python ./gen_req_trace.py ${OUT_NAME} 0 10000000 1g 1
    python ./gen_req_trace.py ${OUT_NAME} "${MAX_KEY}000000" 1g 0
    REQ_TRACE_NAME="$JOB_NAME.out.req.trace"
    python ./plot_key_space_access.py $REQ_TRACE_NAME 1000
    ls ${JOB_NAME}*
    mv ${JOB_NAME}*  ./req-trace/
done
