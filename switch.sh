#!/bin/bash
set -e

IFACE="eth0"
TRACE_ID=${TRACE_ID:?TRACE_ID env variable not set}
TRACE_FILE="/traces/trace_${TRACE_ID}.csv"

echo "[switch] Using trace: $TRACE_FILE"

sysctl -w net.ipv4.ip_forward=1 >/dev/null 2>&1 || true
iptables -t nat -A POSTROUTING -o "$IFACE" -j MASQUERADE 2>/dev/null || true

set_rate() {
    local RATE=$1
    # With delay
    tc qdisc replace dev "$IFACE" root handle 1: netem delay 30ms 5ms
    tc qdisc replace dev "$IFACE" parent 1:1 handle 10: cake bandwidth ${RATE}kbit besteffort flows


    # Without delay
    #tc qdisc replace dev "$IFACE" root cake bandwidth ${RATE}kbit besteffort flows
}

# read trace (skip header)
mapfile -t TRACE_LINES < <(tail -n +2 "$TRACE_FILE")

if [ "${#TRACE_LINES[@]}" -lt 2 ]; then
    echo "Trace too short"
    exit 1
fi

echo "[switch] Loaded ${#TRACE_LINES[@]} trace points"

while true; do
    prev_ts=""

    for line in "${TRACE_LINES[@]}"; do
        IFS=',' read -r ts bw <<< "$line"
        bw=${bw%.*}  # floor to int kbit/s

        set_rate "$bw"
        echo "[switch] rate = ${bw} kbit/s"

        if [ -n "$prev_ts" ]; then
            delta_ms=$((ts - prev_ts))
            if [ "$delta_ms" -gt 0 ]; then
                sleep "$(awk "BEGIN { print $delta_ms / 1000 }")"
            fi
        fi

        prev_ts="$ts"
    done
done
