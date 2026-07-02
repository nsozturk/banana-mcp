#!/usr/bin/env python3
"""Thin shim → banana.cli:main (kept so `python scripts/generate.py ...` works).

The implementation lives in the installable package (banana/cli.py, exposed as
the `banana-generate` console script).
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from banana.cli import main

if __name__ == "__main__":
    main()
