"""Thin async wrapper around gemini_webapi.GeminiClient.

Handles auth from the local cookie jar and exposes a cached singleton so the MCP
server and the CLI scripts reuse one authenticated session (with 1PSIDTS
auto-refresh) instead of re-authenticating per request.
"""
from __future__ import annotations

import asyncio

from gemini_webapi import GeminiClient

from . import config

_client: GeminiClient | None = None
_lock = asyncio.Lock()


async def get_client(verbose: bool = False) -> GeminiClient:
    """Return an initialized, auto-refreshing GeminiClient singleton."""
    global _client
    async with _lock:
        if _client is not None:
            return _client
        psid, psidts = config.auth_pair()
        client = GeminiClient(secure_1psid=psid, secure_1psidts=psidts)
        # auto_refresh keeps __Secure-1PSIDTS rotating so the session survives.
        await client.init(
            timeout=300,
            auto_close=False,
            auto_refresh=True,
            refresh_interval=540,
            verbose=verbose,
        )
        _client = client
        return _client


async def close_client() -> None:
    global _client
    if _client is not None:
        try:
            await _client.close()
        finally:
            _client = None
