#!/bin/sh
# set-loss.sh — run on the MIDDLEBOX container
# Usage:  sh /apps/set-loss.sh <loss_percent>
# Example: sh /apps/set-loss.sh 20   (sets 20% packet loss on eth2)

LOSS=${1:-0}
IFACE="eth2"

echo "[middlebox] Setting packet loss = ${LOSS}% on ${IFACE}"

# Remove existing qdisc (ignore error if none)
tc qdisc del dev ${IFACE} root 2>/dev/null

# Apply new netem rule
tc qdisc add dev ${IFACE} root netem loss ${LOSS}%

echo "[middlebox] Done. Verify with:  tc qdisc show dev ${IFACE}"
tc qdisc show dev ${IFACE}
