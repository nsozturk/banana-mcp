#!/usr/bin/env python3
"""Extract Gemini auth cookies from a browser storage-dump into the cookie file.

Reads a `storagedump_gemini.google.com_*` folder's cookies.json and writes a
clean {name: value} map for the google.com / gemini.google.com domains. Values
are NEVER printed to stdout — only cookie names + presence are reported.

Default output: ~/.config/banana-mcp/cookies.json (what pip/uvx/plugin installs
read). Override with --out (e.g. the repo-local secrets/cookies.json for dev).

Usage:
    python scripts/extract_cookies.py [path/to/storagedump_folder] [--out PATH]
"""
import argparse
import json
import os
import sys
import glob
import stat

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from banana.config import user_cookies_path  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# __Secure-1PSID is mandatory. __Secure-1PSIDTS rotates and some accounts /
# exports don't carry it — it's optional (gemini_webapi refreshes it at runtime).
REQUIRED = ["__Secure-1PSID"]
OPTIONAL = ["__Secure-1PSIDTS"]
KEEP_DOMAINS = (".google.com", ".gemini.google.com", "gemini.google.com")


def find_dump(explicit):
    if explicit:
        return explicit
    cands = sorted(glob.glob(os.path.join(ROOT, "storagedump_gemini.google.com_*")))
    cands = [c for c in cands if os.path.isdir(c)]
    if not cands:
        sys.exit("No storagedump_gemini.google.com_* folder found. Pass the path explicitly.")
    return cands[-1]


def main():
    ap = argparse.ArgumentParser(description="Extract Gemini cookies from a StorageDump export.")
    ap.add_argument("dump", nargs="?", help="Path to a storagedump_gemini.google.com_* folder")
    ap.add_argument("--out", default=user_cookies_path(),
                    help="Output cookie file (default: ~/.config/banana-mcp/cookies.json)")
    args = ap.parse_args()

    dump = find_dump(args.dump)
    cpath = os.path.join(dump, "cookies.json")
    if not os.path.isfile(cpath):
        sys.exit(f"cookies.json not found in {dump}")

    data = json.load(open(cpath))["data"]
    jar = {}
    for c in data:
        dom = c.get("metadata", {}).get("domain", "")
        if dom in KEEP_DOMAINS:
            jar[c["key"]] = c["value"]

    missing = [k for k in REQUIRED if k not in jar]
    if missing:
        sys.exit(f"Missing required cookies: {missing}. Re-export the storage dump while logged in.")

    out = os.path.abspath(os.path.expanduser(args.out))
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w") as f:
        json.dump(jar, f, indent=2)
    os.chmod(out, stat.S_IRUSR | stat.S_IWUSR)  # 600

    # Report names + lengths only — never values.
    print(f"Source dump: {dump}")
    print(f"Wrote {len(jar)} cookies -> {out} (chmod 600)")
    for k in REQUIRED + OPTIONAL:
        if k in jar:
            print(f"  {k}: present (len={len(jar[k])})")
        else:
            print(f"  {k}: MISSING (optional)" if k in OPTIONAL else f"  {k}: MISSING")


if __name__ == "__main__":
    main()
