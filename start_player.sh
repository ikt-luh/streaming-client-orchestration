#!/bin/bash
set -e

echo "[player] Resolving switch IP..."
gw=$(getent hosts switch | awk '{print $1}')

if [ -z "$gw" ]; then
    echo "[player] ERROR: could not resolve switch hostname"
    exit 1
fi

echo "[player] Switch resolved to $gw"

# Replace default gateway
ip route del default || true
ip route add default via "$gw"
echo "[player] Default route now set to switch ($gw)"

# Optional: show routing table
ip route show

# Start player
echo "[player] Starting wrapper.py"
exec python3 /src/wrapper.py
