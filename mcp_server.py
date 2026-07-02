#!/usr/bin/env python3
"""Thin entry shim so `python mcp_server.py` keeps working from a clone.

The server now lives in the installable package at banana/server.py (exposed as
the `banana-mcp` console script). This file just forwards to it.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from banana.server import main

if __name__ == "__main__":
    main()
