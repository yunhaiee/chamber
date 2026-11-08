"""Prints every logged cloud payload as it goes out. Proof from outside the dashboard.

Usage: SH_DB=demo.db .venv/bin/python wire.py --last 0
"""
import argparse
import json
import re
import shutil
import sys
import textwrap
import time
from datetime import datetime

from counsel import db

GOLD = "\033[1;33m"
RESET = "\033[0m"
TAG = re.compile(r"(\[[A-Z]+_\d+\])")


def show(row, include_system):
    width = shutil.get_terminal_size((100, 20)).columns
    when = datetime.fromtimestamp(row["ts"]).strftime("%H:%M:%S")
    print(f"{when}  request {row['request_id']}  {row['user']}")
    if include_system:
        print(textwrap.fill(row["system"] or "", width=width, initial_indent="  sys: ", subsequent_indent="       "))
    for line in textwrap.wrap(row["user_text"] or "", width=width - 2):
        print("  " + TAG.sub(lambda m: f"{GOLD}{m.group(1)}{RESET}", line))
    tags = json.loads(row["tags"] or "[]")
    if tags:
        print("  tags: " + " ".join(f"{GOLD}{t}{RESET}" for t in tags))
    print()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--last", type=int, default=10)
    parser.add_argument("--system", action="store_true")
    args = parser.parse_args()
    sys.stdout.reconfigure(line_buffering=True)
    rows = db.all("SELECT * FROM cloud_payloads ORDER BY id DESC LIMIT ?", args.last) if args.last else []
    for row in reversed(rows):
        show(row, args.system)
    latest = db.one("SELECT MAX(id) id FROM cloud_payloads")
    cursor = (latest["id"] or 0) if latest else 0
    while True:
        for row in db.all("SELECT * FROM cloud_payloads WHERE id>? ORDER BY id", cursor):
            show(row, args.system)
            cursor = row["id"]
        time.sleep(0.5)


if __name__ == "__main__":
    main()
