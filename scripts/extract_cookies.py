#!/usr/bin/env python3
"""Extract Gemini auth cookies from a browser storage-dump into secrets/cookies.json.

Reads the `storagedump_gemini.google.com_*` folder's cookies.json and writes a
clean {name: value} map for the google.com / gemini.google.com domains. Values
are NEVER printed to stdout — only cookie names + presence are reported.

Usage:
    python scripts/extract_cookies.py [path/to/storagedump_folder]
"""
import json
import os
import sys
import glob
import stat

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SECRETS_DIR = os.path.join(ROOT, "secrets")
OUT = os.path.join(SECRETS_DIR, "cookies.json")

# __Secure-1PSID is mandatory. __Secure-1PSIDTS rotates and some accounts /
# exports don't carry it — it's optional (gemini_webapi refreshes it at runtime).
REQUIRED = ["__Secure-1PSID"]
OPTIONAL = ["__Secure-1PSIDTS"]
KEEP_DOMAINS = (".google.com", ".gemini.google.com", "gemini.google.com")


def find_dump():
    if len(sys.argv) > 1:
        return sys.argv[1]
    cands = sorted(glob.glob(os.path.join(ROOT, "storagedump_gemini.google.com_*")))
    cands = [c for c in cands if os.path.isdir(c)]
    if not cands:
        sys.exit("No storagedump_gemini.google.com_* folder found. Pass the path explicitly.")
    return cands[-1]


def main():
    dump = find_dump()
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

    os.makedirs(SECRETS_DIR, exist_ok=True)
    with open(OUT, "w") as f:
        json.dump(jar, f, indent=2)
    os.chmod(OUT, stat.S_IRUSR | stat.S_IWUSR)  # 600

    # Report names + lengths only — never values.
    print(f"Source dump: {dump}")
    print(f"Wrote {len(jar)} cookies -> {OUT} (chmod 600)")
    for k in REQUIRED + OPTIONAL:
        if k in jar:
            print(f"  {k}: present (len={len(jar[k])})")
        else:
            print(f"  {k}: MISSING (optional)" if k in OPTIONAL else f"  {k}: MISSING")


if __name__ == "__main__":
    main()
