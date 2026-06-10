#!/bin/bash
# Start Open vSwitch inside the container and wire up an OpenFlow bridge.
# Usage: start-switch.sh <controller-ip>
# Idempotent: safe to re-run if something didn't attach the first time.
set -e

CTRL_IP="${1:-172.20.20.10}"

# --- start the OVS daemons -------------------------------------------------
mkdir -p /var/run/openvswitch /etc/openvswitch
if [ ! -f /etc/openvswitch/conf.db ]; then
    ovsdb-tool create /etc/openvswitch/conf.db \
        /usr/share/openvswitch/vswitch.ovsschema
fi

# Only start daemons if they aren't already running.
if ! ovs-vsctl show >/dev/null 2>&1; then
    ovsdb-server --remote=punix:/var/run/openvswitch/db.sock \
        --remote=db:Open_vSwitch,Open_vSwitch,manager_options \
        --pidfile --detach --log-file
    ovs-vsctl --no-wait init
    ovs-vswitchd --pidfile --detach --log-file
fi

# --- build the bridge ------------------------------------------------------
ovs-vsctl --may-exist add-br br0
# Speak OpenFlow 1.3 to the controller.
ovs-vsctl set bridge br0 protocols=OpenFlow13
# "secure" => if the controller is unreachable, drop traffic instead of
# falling back to a normal L2 switch. This makes the controller's role obvious.
ovs-vsctl set-fail-mode br0 secure

# If your host kernel can't load the openvswitch module, uncomment the next
# line to use the userspace datapath instead (no kernel module needed):
# ovs-vsctl set bridge br0 datapath_type=netdev

# --- attach every data interface (eth1, eth2, ...) but NOT mgmt eth0 -------
for i in $(ls /sys/class/net | grep -E '^eth[1-9][0-9]*$'); do
    ovs-vsctl --may-exist add-port br0 "$i"
    ip link set "$i" up
done

# --- point the bridge at the Ryu controller --------------------------------
ovs-vsctl set-controller br0 "tcp:${CTRL_IP}:6653"

echo "=== OVS ready (controller tcp:${CTRL_IP}:6653) ==="
ovs-vsctl show
