#!/usr/bin/env python3
"""
Part 0 — Baseline (Unreliable) UDP Receiver
============================================
Collects UDP datagrams until it sees the END marker sent by the sender,
then writes whatever arrived to output.txt.

Key point: dropped datagrams are NEVER requested again.  The output file
will be silently shorter than the input — the receiver has no way to know
anything is missing.

Run:
  python3 receiver_baseline.py
"""

import socket

LISTEN_PORT = 5000
OUTPUT_FILE = "/tmp/output.txt"
TIMEOUT     =  20      # seconds to wait after last datagram before giving up

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.bind(("0.0.0.0", LISTEN_PORT))
sock.settimeout(TIMEOUT)

print(f"[receiver] Listening on UDP :{LISTEN_PORT} ...")
print(f"[receiver] Will give up after {TIMEOUT}s of silence.")

chunks        = []
pkts_received = 0

while True:
    try:
        data, addr = sock.recvfrom(1024)

        if data == b"__END__":
            print(f"[receiver] END marker received — transfer finished.")
            break

        chunks.append(data)
        pkts_received += 1

    except socket.timeout:
        print(f"[receiver] Timed out waiting — sender may have crashed or all")
        print(f"           remaining packets were lost.")
        break

received_bytes = b"".join(chunks)
with open(OUTPUT_FILE, "wb") as f:
    f.write(received_bytes)

print(f"[receiver] Packets received : {pkts_received}")
print(f"[receiver] Bytes written    : {len(received_bytes)} → {OUTPUT_FILE}")
print(f"[receiver] (Run verify.sh on the host to check against the original)")
sock.close()