#!/usr/bin/env python3
"""
Parts 2-4 — Stop-and-Wait Reliable Data Transfer (Receiver)
============================================================
Protocol (mirror of sender_rdt.py)
-----------------------------------
  • Receives framed datagrams:  "<seq_num>|<payload>"
  • Replies "ACK:<seq_num>" for every packet, including duplicates.
  • Duplicate detection: if seq_num < expected, ACKs but discards data.
  • Accepts "__FIN__" datagram and replies "ACK:FIN" to end the session.

The receiver does NOT drop packets — that is the middlebox's job (tc netem).
"""

import socket, os, time

LISTEN_PORT = int(os.environ.get("RECEIVER_PORT", "5000"))
OUTPUT_FILE = os.environ.get("OUTPUT_FILE", "/tmp/output.txt")

FIN_MARKER = b"__FIN__"

def receive_file():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(("0.0.0.0", LISTEN_PORT))

    print(f"[receiver] Listening on UDP :{LISTEN_PORT} …")

    expected_seq = 0
    chunks       = {}      # seq -> bytes
    pkts_rcvd    = 0
    pkts_dup     = 0
    t_start      = None

    while True:
        data, addr = sock.recvfrom(65535)

        # ── FIN: end-of-transfer ─────────────────────────────────────────────
        # Check using the unambiguous __FIN__ marker BEFORE trying to parse
        # as a data frame, so there is zero chance of a seq|payload packet
        # being mistaken for a termination signal.
        if data == FIN_MARKER:
            sock.sendto(b"ACK:FIN", addr)
            print("[receiver] FIN received — transfer done.")
            break

        # ── Data packet ──────────────────────────────────────────────────────
        pkts_rcvd += 1
        if t_start is None:
            t_start = time.time()

        # Parse frame: "<seq>|<payload>"
        try:
            sep     = data.index(b"|")
            seq     = int(data[:sep])
            payload = data[sep+1:]
        except (ValueError, IndexError):
            # Malformed — could be a stray packet; skip silently
            print(f"[receiver] Malformed packet ({len(data)} B), ignoring.")
            continue

        # Always ACK — even duplicates — so the sender can advance
        sock.sendto(f"ACK:{seq}".encode(), addr)

        if seq == expected_seq:
            chunks[seq] = payload
            expected_seq += 1
            print(f"[receiver] ✓ seq {seq:4d}  {len(payload)} B  → ACK sent")
        elif seq < expected_seq:
            pkts_dup += 1
            print(f"[receiver] dup seq {seq:4d}  (expected {expected_seq}) → ACK re-sent")
        else:
            # Should not happen in stop-and-wait; means a packet arrived out of order
            print(f"[receiver] !! out-of-order seq {seq}, expected {expected_seq} — ignoring")

    # ── Reassemble and write ─────────────────────────────────────────────────
    ordered = b"".join(chunks[i] for i in sorted(chunks))
    with open(OUTPUT_FILE, "wb") as f:
        f.write(ordered)

    elapsed = time.time() - t_start if t_start else 0
    print()
    print("=" * 45)
    print(f"  Received {len(ordered)} bytes → {OUTPUT_FILE}")
    print(f"  Unique packets   : {len(chunks)}")
    print(f"  Duplicate packets: {pkts_dup}")
    print(f"  Transfer time    : {elapsed:.2f} s")
    print("=" * 45)
    sock.close()

if __name__ == "__main__":
    receive_file()