#!/bin/bash
set -e

IFACE="eth0"
BANDWIDTH_MIN=${BANDWIDTH_MIN:-500}      # kbit/s
BANDWIDTH_MAX=${BANDWIDTH_MAX:-5000}     # kbit/s
INTERVAL=${INTERVAL:-1}                  # seconds

echo "[switch] Simulating bandwidth between $BANDWIDTH_MIN and $BANDWIDTH_MAX kbit/s"

sysctl -w net.ipv4.ip_forward=1 >/dev/null 2>&1 || true
iptables -t nat -A POSTROUTING -o $IFACE -j MASQUERADE 2>/dev/null || true

set_rate() {
    RATE=$1
    tc qdisc replace dev eth0 root handle 1: netem delay 30ms 5ms 
    tc qdisc replace dev "$IFACE" parent 1:1 handle 10: cake bandwidth ${RATE}kbit besteffort flows

    #tc qdisc replace dev "$IFACE" root cake \
        #bandwidth ${RATE}kbit besteffort flows nat \
        #rtt 30ms

    #tc qdisc replace dev $IFACE root cake bandwidth ${RATE}kbit besteffort flows
}

# initial rate
RATE=$((RANDOM % (BANDWIDTH_MAX - BANDWIDTH_MIN + 1) + BANDWIDTH_MIN))
set_rate $RATE
echo "[switch] initial rate = ${RATE} kbit/s"

while true; do
    RATE=$((RANDOM % (BANDWIDTH_MAX - BANDWIDTH_MIN + 1) + BANDWIDTH_MIN))
    set_rate $RATE
    echo "[switch] rate = ${RATE} kbit/s"
    sleep $INTERVAL
done
