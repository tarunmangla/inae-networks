#!/usr/bin/env python3
"""
Part 0 — Baseline (Unreliable) UDP Sender
==========================================
Reads input.txt and sends it chunk by chunk over UDP — no ACKs, no sequence
numbers, no retransmissions.  Each chunk is a separate datagram; the receiver
is expected to reassemble them in arrival order.

On a perfect network this works fine.
With packet loss the receiver silently gets an incomplete file — and neither
side knows it.

Run:
  python3 sender_baseline.py
"""

import socket

RECEIVER_IP   = "10.0.2.1"
RECEIVER_PORT = 5000
INPUT_FILE    = "/tmp/input.txt"
CHUNK_SIZE    = 512          # bytes per datagram — well within UDP safe limit

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

with open(INPUT_FILE, "rb") as f:
    data = f.read()

total_chunks = (len(data) + CHUNK_SIZE - 1) // CHUNK_SIZE
print(f"[sender] File      : {len(data)} bytes")
print(f"[sender] Chunks    : {total_chunks} × {CHUNK_SIZE} B datagrams")
print(f"[sender] Sending to {RECEIVER_IP}:{RECEIVER_PORT} with NO reliability ...")

for i in range(0, len(data), CHUNK_SIZE):
    chunk = data[i:i+CHUNK_SIZE]
    sock.sendto(chunk, (RECEIVER_IP, RECEIVER_PORT))

# Send a special END marker so the receiver knows to stop listening
sock.sendto(b"__END__", (RECEIVER_IP, RECEIVER_PORT))
print("[sender] Done — no ACKs, no guarantees.")
sock.close()