#!/usr/bin/env python3
"""
Parts 2-4 — Stop-and-Wait Reliable Data Transfer (Sender)
==========================================================
Protocol
--------
  • File is split into CHUNK_SIZE-byte chunks.
  • Each chunk is framed as:   <seq_num>|<payload bytes>
    where seq_num is a monotonically increasing integer.
  • Sender waits for "ACK:<seq_num>" before moving to the next chunk.
  • If no ACK arrives within TIMEOUT seconds, the chunk is retransmitted.
  • A special "FIN" datagram signals end-of-transfer; receiver replies "ACK:FIN".

Environment (override via env vars):
  RECEIVER_IP   default 10.0.2.1
  CHUNK_SIZE    default 512  (bytes per packet)
  TIMEOUT       default 1.0  (seconds)
"""

import socket, time, os

RECEIVER_IP   = os.environ.get("RECEIVER_IP",  "10.0.2.1")
RECEIVER_PORT = int(os.environ.get("RECEIVER_PORT", "5000"))
INPUT_FILE    = os.environ.get("INPUT_FILE",   "/tmp/input.txt")
CHUNK_SIZE    = int(os.environ.get("CHUNK_SIZE",   "512"))
TIMEOUT       = float(os.environ.get("TIMEOUT",     "1.0"))

def send_file():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.settimeout(TIMEOUT)

    with open(INPUT_FILE, "rb") as f:
        raw = f.read()

    chunks = [raw[i:i+CHUNK_SIZE] for i in range(0, len(raw), CHUNK_SIZE)]
    total  = len(chunks)

    packets_sent  = 0
    retransmits   = 0
    t_start       = time.time()

    print(f"[sender] File size : {len(raw)} bytes")
    print(f"[sender] Chunks    : {total}  ({CHUNK_SIZE} B each)")
    print(f"[sender] Timeout   : {TIMEOUT} s")
    print()

    for seq, chunk in enumerate(chunks):
        # Frame:  "<seq>|<data>"
        packet = f"{seq}|".encode() + chunk

        while True:
            sock.sendto(packet, (RECEIVER_IP, RECEIVER_PORT))
            packets_sent += 1

            try:
                ack_data, _ = sock.recvfrom(256)

                # Guard against garbled/binary datagrams from a previous run
                try:
                    ack = ack_data.decode().strip()
                except UnicodeDecodeError:
                    print(f"[sender] ? unreadable datagram received, ignoring")
                    continue

                if ack == f"ACK:{seq}":
                    print(f"[sender] ✓ ACK {seq:4d}  ({seq+1}/{total})")
                    break
                else:
                    # Could be a delayed ACK from a previous retransmit — safe to ignore
                    print(f"[sender] ? unexpected '{ack}' (want ACK:{seq}), retrying")
                    retransmits += 1

            except socket.timeout:
                print(f"[sender] ✗ timeout on seq {seq}, retransmitting …")
                retransmits += 1

    # Send FIN — retry until ACK:FIN comes back
    while True:
        sock.sendto(b"__FIN__", (RECEIVER_IP, RECEIVER_PORT))
        try:
            ack_data, _ = sock.recvfrom(256)
            try:
                if ack_data.decode().strip() == "ACK:FIN":
                    break
            except UnicodeDecodeError:
                pass
        except socket.timeout:
            print("[sender] ✗ timeout waiting for ACK:FIN, retrying …")

    elapsed = time.time() - t_start
    sock.close()

    print()
    print("=" * 45)
    print(f"  Transfer complete in {elapsed:.2f} s")
    print(f"  Packets sent (incl. retransmits) : {packets_sent}")
    print(f"  Retransmissions                  : {retransmits}")
    print(f"  Effective throughput             : "
          f"{len(raw)/elapsed/1024:.1f} KB/s")
    print("=" * 45)

if __name__ == "__main__":
    send_file()