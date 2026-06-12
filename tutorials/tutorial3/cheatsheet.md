# Containerlab Networking Cheat Sheet

## The 20 Commands You'll Use 90% of the Time

## 0. Build a Custom Docker Image

If you have a Dockerfile in a folder and want Containerlab nodes to use that image:

```bash
docker build -t <image-name>:latest <folder_name>
```

Example:

```bash
docker build -t network-lab:latest .
```

Verify the image exists:

```bash
docker images
```

Example output:

```text
REPOSITORY    TAG      IMAGE ID
network-lab   latest   abc123def456
```

You can then reference this image in your topology:

```yaml
topology:
  nodes:
    client:
      kind: linux
      image: network-lab:latest
```

---

## 0.1 Install Networking Tools Inside Running Nodes

Many minimal Linux images do not include tools such as:

* tcpdump
* ping
* traceroute
* iperf3

Install them after deployment:

```bash
sudo docker exec clab-linear-client sh -c "apk add --no-cache tcpdump iputils iperf3 traceroute"
```

```bash
sudo docker exec clab-linear-router sh -c "apk add --no-cache tcpdump iputils iperf3 traceroute"
```

```bash
sudo docker exec clab-linear-server sh -c "apk add --no-cache tcpdump iputils iperf3 traceroute"
```

Verify installation:

```bash
docker exec -it clab-linear-client sh
```

```bash
which tcpdump
which ping
which traceroute
which iperf3
```

Expected:

```text
/usr/sbin/tcpdump
/bin/ping
/usr/bin/traceroute
/usr/bin/iperf3
```


---

## 1. Start a Lab

Deploy your topology:

```bash
sudo clab deploy -t topology.yaml
```

Check if everything started:

```bash
sudo clab inspect -t topology.yaml
```

Expected output:

```text
clab-linear-client
clab-linear-router
clab-linear-server
```

---

## 2. Enter a Node

Open a shell inside a Containerlab node:

```bash
docker exec -it clab-linear-client sh
```

Examples:

```bash
docker exec -it clab-linear-router sh
docker exec -it clab-linear-server sh
```

Exit when finished:

```bash
exit
```

---

## 3. Check Interface Configuration

See all interfaces:

```bash
ip addr show
```

See one interface:

```bash
ip addr show eth1
```

Look for:

```text
inet 10.0.1.1/24
UP
```

If the interface is **UP** and has an IP address, you're good.

---

## 4. Check Routes

Show routing table:

```bash
ip route show
```

Example:

```text
10.0.2.0/24 via 10.0.1.2 dev eth1
```

Meaning:

> To reach 10.0.2.0/24, send packets to router 10.0.1.2.

---

## 5. Check Routing Rules

```bash
ip rule show
```

Normally you'll see:

```text
0:      from all lookup local
32766:  from all lookup main
32767:  from all lookup default
```

Usually just verify they exist.

---

## 6. Turn a Linux Host into a Router

Enable forwarding:

```bash
sysctl -w net.ipv4.ip_forward=1
```

Verify:

```bash
sysctl net.ipv4.ip_forward
```

Expected:

```text
net.ipv4.ip_forward = 1
```

---

## 7. Test Connectivity

Ping another node:

```bash
ping 10.0.2.1
```

Send only four packets:

```bash
ping -c 4 10.0.2.1
```

Expected:

```text
4 packets transmitted
4 received
0% packet loss
```

---

## 8. See the Route Packets Take

```bash
traceroute 10.0.2.1
```

Useful when debugging routing problems.

---

## 9. Capture Traffic

Capture packets:

```bash
tcpdump -i eth1
```

Show raw IPs:

```bash
tcpdump -i eth1 -n
```

Verbose output:

```bash
tcpdump -i eth1 -n -v
```

Capture only ICMP:

```bash
tcpdump -i eth1 icmp
```

Stop the capture with:

`Ctrl + C`

---

## 10. Measure Throughput

Start server:

```bash
iperf3 -s
```

Run client:

```bash
iperf3 -c 10.0.2.1
```

10-second test:

```bash
iperf3 -c 10.0.2.1 -t 10
```

---

## 11. Measure Packet Loss

UDP mode:

```bash
iperf3 -c 10.0.2.1 -u -b 5M -t 10
```

Look for:

```text
Lost/Total Datagrams
```

---

## 12. Add Latency

Simulate a WAN:

```bash
tc qdisc add dev eth1 root netem delay 50ms
```

Check:

```bash
ping -c 10 10.0.2.1
```

RTT should increase.

---

## 13. Add Jitter

Simulate unstable latency:

```bash
tc qdisc add dev eth1 root netem delay 50ms 10ms
```

Meaning:

```text
50 ms ± 10 ms
```

---

## 14. Add Packet Loss

Drop 5% of packets:

```bash
tc qdisc add dev eth1 root netem loss 5%
```

Combine delay and loss:

```bash
tc qdisc add dev eth1 root netem delay 50ms loss 2%
```

---

## 15. Limit Bandwidth

Limit a link to 10 Mbps:

```bash
tc qdisc add dev eth1 root tbf \
    rate 10mbit \
    burst 32kbit \
    latency 50ms
```

Verify:

```bash
iperf3 -c SERVER_IP
```

Expected:

```text
~10 Mbit/s
```

---

## 16. Simulate a Real WAN Link

Apply bandwidth limiting:

```bash
tc qdisc add dev eth1 root handle 1: tbf \
    rate 10mbit \
    burst 32kbit \
    latency 50ms
```

Then add delay and loss:

```bash
tc qdisc add dev eth1 parent 1:1 handle 10: \
    netem delay 50ms loss 1%
```

Result:

```text
10 Mbps bandwidth
50 ms latency
1% packet loss
```

---

## 17. Check Active tc Rules

```bash
tc qdisc show dev eth1
```

You'll see entries such as:

```text
netem
tbf
```

if shaping is active.

---

## 18. Remove All Traffic Shaping

```bash
tc qdisc del dev eth1 root
```

This is the command students forget most often.

---

## 19. DNS Tools

Quick lookup:

```bash
nslookup google.com
```

Detailed lookup:

```bash
dig google.com
```

---

## 20. Destroy the Lab

When finished:

```bash
sudo clab destroy -t topology.yaml
```

Everything is removed:

* Containers
* Links
* Virtual cables
* Temporary configurations

---

## Typical Workflow During a Lab

```bash
# Deploy
clab deploy -t topology.yaml

# Verify
clab inspect -t topology.yaml

# Enter a node
docker exec -it clab-node sh

# Check configuration
ip addr show
ip route show
ip rule show

# Test connectivity
ping DEST_IP
traceroute DEST_IP

# Observe traffic
tcpdump -i eth1 -n -v

# Measure throughput
iperf3 -s
iperf3 -c SERVER_IP -t 10

# Emulate WAN conditions
tc qdisc add dev eth1 root netem delay 50ms
tc qdisc add dev eth1 root tbf rate 10mbit burst 32kbit latency 50ms

# Remove shaping
tc qdisc del dev eth1 root

# Cleanup
clab destroy -t topology.yaml
```

## If Something Doesn't Work, Check These Three Commands First

```bash
ip addr show
ip route show
ip rule show
```

In real networking labs, these three commands solve most problems before you even start using `ping`, `tcpdump`, `iperf3`, or `tc`.
