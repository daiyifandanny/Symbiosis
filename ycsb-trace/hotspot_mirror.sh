#! /bin/bash


set -e

function run_one_hotspot_pair() {
    HOTSPOT_KEY_PCT=$1
    HOTSPOT_OP_PCT=$2
    for MAX_KEY in 10 20 25 40 50 80
    do
        JOB_NAME="Job_hotspot-NumAccess_10M-Maxkey_${MAX_KEY}M-HotspotKeyPct-${HOTSPOT_KEY_PCT}_HotspotOpPct-${HOTSPOT_OP_PCT}"
        echo $JOB_NAME
        REQ_TRACE_NAME="req-trace-hotspot/$JOB_NAME.out.req.trace"
        python hotspot_mirror.py $REQ_TRACE_NAME "${MAX_KEY}000000"
    done
}

run_one_hotspot_pair 10 90
run_one_hotspot_pair 20 80
run_one_hotspot_pair 30 70


