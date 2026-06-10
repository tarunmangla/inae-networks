# A 1-Hour SDN Tutorial with Containerlab + Ryu

Build a software-defined network from scratch, watch packets get punted to a
controller, turn a dumb hub into a self-learning switch, and finish by writing
a firewall as a few lines of flow rules.

**You only need a Linux host with Docker and containerlab.** Open vSwitch runs
*inside* the lab containers, so there is nothing to install on the host and
nothing to clean up afterwards.

---

## What you'll build

<img src="images/sdn.png" alt="SDN topology" width="700">


One controller, one OpenFlow switch, three hosts on `10.0.0.0/24`.

## Timing (≈60 min)

| Time   | Section |
|--------|---------|
| 0–10   | 0. Setup & deploy |
| 10–15  | 1. Connect the switch to the controller |
| 15–35  | 2. Hub (packet-in everything) vs. self-learning switch |
| 35–55  | 3. Build a firewall |
| 55–60  | 4. Wrap-up & teardown |

---

## 0. Setup (do the image builds *before* the session)

### Prerequisites
- Docker and [containerlab](https://containerlab.dev/install/) installed.
- The Open vSwitch kernel module available on the host:
  ```bash
  sudo modprobe openvswitch
  ```
  (If your host can't load it, see *Troubleshooting* — there's a one-line
  userspace fallback.)

### Files in this folder
```
Dockerfile.node     # OVS + ping/iperf/tcpdump — used for switches AND hosts
Dockerfile.ryu      # Ryu controller (with the version pins that make it run)
start-switch.sh     # boots OVS and wires up br0 inside the switch container
sdn.clab.yml        # the containerlab topology
apps/hub.py         # exercise 2: dumb hub
apps/firewall.py    # exercise 3: firewall
```

### Build the two images
```bash
docker build -t sdn-node:latest -f Dockerfile.node .
docker build -t sdn-ryu:latest  -f Dockerfile.ryu  .
```

### Deploy the lab
```bash
sudo containerlab deploy -t sdn.clab.yml
```
You should see a table listing `clab-sdn-ctrl`, `clab-sdn-s1`, `clab-sdn-h1/2/3`.

> **Tip:** open three terminals — one for the **controller**, one for the
> **switch**, one for **hosts**. You'll switch between them constantly.

---

## 1. Connect the switch to the controller (5 min)

When the lab deployed, `start-switch.sh` already built `br0`, attached the three
host links, and pointed the bridge at `tcp:172.20.20.10:6653`. But nothing is
listening there yet, so the switch is connected to nobody.

**Switch terminal** — confirm the bridge exists and *who* it's looking for:
```bash
docker exec -it clab-sdn-s1 ovs-vsctl show
```
Look at the `Controller "tcp:172.20.20.10:6653"` line. Right now it will say
`is_connected: false`.

**Controller terminal** — start the simplest possible app:
```bash
docker exec -it clab-sdn-ctrl python -m ryu.cmd.manager ryu.app.simple_switch_13
```
Leave it running. Within a second or two, Ryu logs that switch `1` connected.

**Switch terminal** — check again:
```bash
docker exec -it clab-sdn-s1 ovs-vsctl show
```
Now `is_connected: true`. And the flow table is no longer empty:
```bash
docker exec -it clab-sdn-s1 ovs-ofctl -O OpenFlow13 dump-flows br0
```
You'll see one rule with `priority=0 actions=CONTROLLER` — the **table-miss**
entry the controller installed. It means *"anything I don't have a rule for,
send to me."*

**Concept:** the data plane (OVS) and control plane (Ryu) are separate programs
talking OpenFlow over a TCP socket. The switch starts dumb; the controller
programs its behaviour.

Stop the controller for now: `Ctrl-C` in the controller terminal.

---

## 2. Hub vs. self-learning switch (20 min)

### 2a. The dumb hub — everything goes to the controller

**Controller terminal:**
```bash
docker exec -it clab-sdn-ctrl python -m ryu.cmd.manager hub.py
```
`hub.py` floods every packet and **installs no forwarding rules**, so each
packet keeps coming back to the controller.

**Host terminal** — generate a little traffic:
```bash
docker exec -it clab-sdn-h1 ping -c 4 10.0.0.2
```

Ping works. Now look at the controller terminal: you get a `PacketIn ... FLOOD`
log line for **every packet** (each echo request and reply, plus ARP).

**iperf** - for throughput test
```bash
 docker exec -it clab-sdn-h3 iperf3 -s
```
change terminal

```bash
 docker exec -it clab-sdn-h1 iperf3 -c 10.0.0.3 -t 10
```

**Switch terminal** — confirm nothing was learned:
```bash
docker exec -it clab-sdn-s1 ovs-ofctl -O OpenFlow13 dump-flows br0
```
Still just the `priority=0 actions=CONTROLLER` rule, and its packet counter
climbs with every ping. The switch is doing zero thinking — the controller is
in the path of every single packet. That does not scale.

Stop the hub (`Ctrl-C`).

### 2b. The self-learning switch — install flows, get out of the way

**Switch terminal** — wipe the table so we start clean:
```bash
docker exec -it clab-sdn-s1 ovs-ofctl -O OpenFlow13 del-flows br0
```

**Controller terminal** — run the learning switch:
```bash
docker exec -it clab-sdn-ctrl ryu-manager ryu.app.simple_switch_13
```

**Host terminal:**
```bash
docker exec -it clab-sdn-h1 ping -c 4 10.0.0.2
```
Watch the difference: the controller logs only the **first** packet or two,
then goes quiet. Once it has learned which MAC lives on which port, it installs
a flow rule and the switch handles the rest by itself.

**iperf** - for throughput test
```bash
 docker exec -it clab-sdn-h3 iperf3 -s
```
change terminal

```bash
 docker exec -it clab-sdn-h1 iperf3 -c 10.0.0.3 -t 10
```

**Switch terminal:**
```bash
docker exec -it clab-sdn-s1 ovs-ofctl -O OpenFlow13 dump-flows br0
```
Now you see real forwarding rules, e.g. matches on `in_port`/`eth_src`/`eth_dst`
with `actions=output:<port>`. Ping again and you'll see the **n_packets**
counters on those rules go up while the controller stays silent.

**Concept:** this is *reactive* SDN. The controller is consulted only for the
first packet of a flow; after that the decision is cached as a flow rule in the
switch. Same connectivity, a tiny fraction of the controller load.

> **Discussion prompt:** what happens to an existing flow if a host moves to a
> different port? (Hint: the learned rule and the `idle_timeout`.)

Stop the controller (`Ctrl-C`).

---

## 3. Build a firewall (20 min)

A firewall in SDN is just **higher-priority flow rules whose action is "drop"**.
`apps/firewall.py` is the learning switch from 2b plus a policy:

> Block ICMP (ping) between **h1 (10.0.0.1)** and **h3 (10.0.0.3)**, both
> directions. Everything else flows normally.

The relevant lines:
```python
BLOCK_ICMP = [("10.0.0.1", "10.0.0.3")]
...
match = parser.OFPMatch(eth_type=0x0800, ip_proto=1,   # IPv4, ICMP
                        ipv4_src=src, ipv4_dst=dst)
self.add_flow(dp, 100, match, [])   # priority 100, empty actions = DROP
```
Priority `100` beats the learned forwarding rules (priority `1`), so blocked
packets are dropped before they're ever forwarded.

**Switch terminal** — clean slate:
```bash
docker exec -it clab-sdn-s1 ovs-ofctl -O OpenFlow13 del-flows br0
```

**Controller terminal:**
```bash
docker exec -it clab-sdn-ctrl python -m ryu.cmd.manager firewall.py
```
It logs the two drop rules it installs.

**Host terminal** — test the policy:
```bash
docker exec -it clab-sdn-h1 ping -c 3 10.0.0.2    # h1 -> h2: WORKS
docker exec -it clab-sdn-h1 ping -c 3 10.0.0.3    # h1 -> h3: BLOCKED (100% loss)
docker exec -it clab-sdn-h3 ping -c 3 10.0.0.2    # h3 -> h2: WORKS
```

**Switch terminal** — see the firewall in the flow table:
```bash
docker exec -it clab-sdn-s1 ovs-ofctl -O OpenFlow13 dump-flows br0
```
The `priority=100 ... icmp ... actions=drop` rules show a rising `n_packets`
counter each time you try the blocked ping — proof the drop is happening in the
switch hardware path, not at the controller.

### Make it yours (pick one, ~5 min)
- Block **all** traffic between h1 and h3 (drop on `eth_type=0x0800` with the IP
  pair, no `ip_proto`). Does ARP still pass? Why does that matter?
- Block a **TCP port** instead: `ip_proto=6, tcp_dst=5201`, then test with
  `iperf3 -s` on one host and `iperf3 -c <ip>` on another.
- Add a third host to the blocklist by editing `BLOCK_ICMP` and restarting Ryu.

**Concept:** policy is just code that emits flow rules. Change the Python,
restart the controller, and the network's behaviour changes — no per-switch CLI
config.

---

## 4. Wrap-up & teardown (5 min)

You went from raw Open vSwitch to a programmable firewall by changing only which
Python app the controller runs. The three big ideas:

1. **Separation of planes** — OVS forwards; Ryu decides. They meet over OpenFlow.
2. **Table-miss → packet-in → flow-mod** is the core SDN loop. Punting every
   packet (the hub) doesn't scale; caching decisions as flows (the learning
   switch) does.
3. **A firewall is just prioritized flow rules.** Match + drop. Same machinery
   builds routing, load balancing, QoS, and more.

Tear down (removes everything, no host residue):
```bash
sudo containerlab destroy -t sdn.clab.yml --cleanup
```

---

## Troubleshooting

**Switch shows `is_connected: false`.** Make sure the controller app is actually
running (`ryu-manager ...` in the foreground). Check reachability:
`docker exec clab-sdn-s1 ping -c1 172.20.20.10`.

**`ovs-vswitchd` won't start / no datapath.** Your host kernel can't load the
`openvswitch` module. Edit `start-switch.sh`, uncomment the
`datapath_type=netdev` line (userspace datapath, no module needed), then
redeploy. Or run `sudo modprobe openvswitch` on the host first.

**`s1` has no eth1/eth2/eth3 in the bridge.** The setup ran before the links
were ready. Re-run it (it's idempotent):
`docker exec clab-sdn-s1 bash /start-switch.sh 172.20.20.10`.

**Ryu crashes on import (`ssl`/`eventlet`/`dnspython` errors).** You changed the
pinned versions in `Dockerfile.ryu`. Keep `ryu==4.34`, `eventlet==0.30.2`,
`dnspython==1.16.0`, Python 3.9.

**Pings between two hosts that should work still fail.** Clear stale flows:
`docker exec clab-sdn-s1 ovs-ofctl -O OpenFlow13 del-flows br0`, then ping again.

## Handy command reference
```bash
# bridge state + controller connection
docker exec -it clab-sdn-s1 ovs-vsctl show
# flow table (always pass -O OpenFlow13)
docker exec -it clab-sdn-s1 ovs-ofctl -O OpenFlow13 dump-flows br0
# clear all flows
docker exec -it clab-sdn-s1 ovs-ofctl -O OpenFlow13 del-flows br0
# watch OpenFlow on the wire
docker exec -it clab-sdn-ctrl tcpdump -nni eth0 tcp port 6653
```
