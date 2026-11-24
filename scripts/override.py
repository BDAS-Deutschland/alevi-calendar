#!/usr/bin/env python3
"""Manage manual data in data/overrides.json (this file is never touched by the scraper).

    python3 scripts/override.py list
    python3 scripts/override.py add hz-ali-todestag 2026-03-10                    # one-day event
    python3 scripts/override.py add muharrem 2026-06-16 2026-06-27 --reason "..."  # with end date
    python3 scripts/override.py fix 2030-hidirellez --start 2030-05-05 --end 2030-05-06 --reason "..."
    python3 scripts/override.py remove 2027-sivas --reason "..."   # hide a scraped event
    python3 scripts/override.py drop 2026-hz-ali-todestag          # delete a manual entry again
    python3 scripts/override.py keys                               # list valid event keys

The event id is "<year>-<key>". Add --build to rebuild dist/ right away.
"""
import argparse
import datetime as dt
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FILE = ROOT / "data" / "overrides.json"
CATALOG = ROOT / "data" / "catalog.json"


def date(s):
    try:
        return dt.date.fromisoformat(s).isoformat()
    except ValueError:
        raise argparse.ArgumentTypeError(f"'{s}' is not a date (YYYY-MM-DD)")


def load():
    return json.loads(FILE.read_text(encoding="utf-8"))


def save(data):
    tmp = FILE.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(FILE)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("list")
    sub.add_parser("keys")
    a = sub.add_parser("add", help="insert an event the source does not have")
    a.add_argument("key")
    a.add_argument("start", type=date)
    a.add_argument("end", type=date, nargs="?")
    a.add_argument("--reason", default="")
    f = sub.add_parser("fix", help="change dates of a scraped event")
    f.add_argument("id")
    f.add_argument("--start", type=date)
    f.add_argument("--end", type=date)
    f.add_argument("--reason", default="")
    r = sub.add_parser("remove", help="hide a scraped event")
    r.add_argument("id")
    r.add_argument("--reason", default="")
    d = sub.add_parser("drop", help="delete a manual add/fix/remove entry")
    d.add_argument("id")
    for p in (a, f, r, d):
        p.add_argument("--build", action="store_true", help="rebuild dist/ afterwards")
    args = ap.parse_args()

    data = load()
    data.setdefault("fix", {})
    data.setdefault("add", [])
    data.setdefault("remove", [])
    keys = json.loads(CATALOG.read_text(encoding="utf-8"))["events"]

    if args.cmd == "keys":
        for k, v in keys.items():
            print(f"{k:18} {v['title']['de']}")
        return
    if args.cmd == "list":
        for e in sorted(data["add"], key=lambda e: e["start"]):
            print(f"add     {e['id']:28} {e['start']} – {e['end']}  {e.get('reason', '')}")
        for eid, fx in sorted(data["fix"].items()):
            print(f"fix     {eid:28} {fx.get('start', '')} – {fx.get('end', '')}  {fx.get('reason', '')}")
        for eid in data["remove"]:
            print(f"remove  {eid}")
        if not (data["add"] or data["fix"] or data["remove"]):
            print("(no manual entries)")
        return

    if args.cmd == "add":
        if args.key not in keys:
            sys.exit(f"unknown key '{args.key}'. Valid keys: {', '.join(keys)}")
        end = args.end or args.start
        if end < args.start:
            sys.exit("end is before start")
        eid = f"{args.start[:4]}-{args.key}"
        entry = {"id": eid, "key": args.key, "start": args.start, "end": end}
        if args.reason:
            entry["reason"] = args.reason
        replaced = any(e["id"] == eid for e in data["add"])
        data["add"] = [e for e in data["add"] if e["id"] != eid] + [entry]
        data["add"].sort(key=lambda e: e["start"])
        print(("updated " if replaced else "added ") + f"{eid}: {args.start} – {end}")
    elif args.cmd == "fix":
        if not (args.start or args.end):
            sys.exit("give --start and/or --end")
        fx = data["fix"].get(args.id, {})
        if args.start:
            fx["start"] = args.start
        if args.end:
            fx["end"] = args.end
        if args.reason:
            fx["reason"] = args.reason
        data["fix"][args.id] = fx
        print(f"fix {args.id}: {fx}")
    elif args.cmd == "remove":
        if args.id not in data["remove"]:
            data["remove"].append(args.id)
        print(f"{args.id} will be hidden")
    elif args.cmd == "drop":
        n = len(data["add"]) + len(data["fix"]) + len(data["remove"])
        data["add"] = [e for e in data["add"] if e["id"] != args.id]
        data["fix"].pop(args.id, None)
        data["remove"] = [x for x in data["remove"] if x != args.id]
        if n == len(data["add"]) + len(data["fix"]) + len(data["remove"]):
            sys.exit(f"no manual entry for {args.id}")
        print(f"dropped manual entries for {args.id}")

    save(data)
    if args.build:
        subprocess.run([sys.executable, str(ROOT / "scripts" / "build.py")], check=True)


if __name__ == "__main__":
    main()
