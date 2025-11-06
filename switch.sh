#!/bin/bash
set -e

IFACE="eth0"
BANDWIDTH_MIN=${BANDWIDTH_MIN:-500}   # in kbit/s
BANDWIDTH_MAX=${BANDWIDTH_MAX:-5000}  # in kbit/s
INTERVAL=${INTERVAL:-1.0}             # seconds

echo "[switch] Starting with rate range ${BANDWIDTH_MIN}-${BANDWIDTH_MAX} kbit/s, interval ${INTERVAL}s"

# Enable IP forwarding and NAT
sysctl -w net.ipv4.ip_forward=1 >/dev/null
iptables -t nat -A POSTROUTING -o $IFACE -j MASQUERADE

# Apply initial qdisc
RATE=$((RANDOM % (BANDWIDTH_MAX - BANDWIDTH_MIN + 1) + BANDWIDTH_MIN))
tc qdisc replace dev $IFACE root tbf rate ${RATE}kbit burst 32kbit latency 400ms

# Main loop: randomize every INTERVAL seconds
while true; do
    RATE=$((RANDOM % (BANDWIDTH_MAX - BANDWIDTH_MIN + 1) + BANDWIDTH_MIN))
    tc qdisc replace dev $IFACE root tbf rate ${RATE}kbit burst 32kbit latency 400ms
    echo "[switch] rate=${RATE} kbit/s"
    sleep $INTERVAL
done