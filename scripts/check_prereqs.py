#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Run this before /execute 9 to verify the full toolchain is present.
Usage: python scripts/check_prereqs.py
"""
import subprocess, sys

# Force UTF-8 output on Windows so ✓/✗/─ render correctly
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

CHECKS = [
    ("cargo",   ["cargo", "--version"],   "https://rustup.rs/"),
    ("rustup",  ["rustup", "--version"],  "https://rustup.rs/"),
    ("node",    ["node", "--version"],    "https://nodejs.org/"),
    ("npm",     ["npm", "--version"],     "https://nodejs.org/"),
]

RUST_TARGET = "x86_64-pc-windows-msvc"

def run(cmd: list[str]) -> str | None:
    try:
        return subprocess.check_output(cmd, stderr=subprocess.STDOUT, text=True).strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None

ok = True
print("ZENO Phase 9 — Toolchain Prerequisites\n" + "─" * 40)
for name, cmd, url in CHECKS:
    result = run(cmd)
    if result:
        print(f"  ✓ {name:8s}  {result}")
    else:
        print(f"  ✗ {name:8s}  NOT FOUND  →  Install from: {url}")
        ok = False

# Check Rust Windows target
targets = run(["rustup", "target", "list", "--installed"]) or ""
if RUST_TARGET in targets:
    print(f"  ✓ rust target  {RUST_TARGET}")
else:
    print(f"  ✗ rust target  {RUST_TARGET} missing")
    print(f"    Fix: rustup target add {RUST_TARGET}")
    ok = False

print()
if ok:
    print("All prerequisites satisfied. Proceed with /execute 9.")
    sys.exit(0)
else:
    print("Fix the above before executing Phase 9.")
    sys.exit(1)
