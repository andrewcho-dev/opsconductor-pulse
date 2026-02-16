"""
Traced HTTP client for cross-service trace propagation.

Usage:
    from shared.http_client import traced_client

    async with traced_client(timeout=10.0) as client:
        resp = await client.get("http://other-service/api/data")
        # X-Trace-ID header is automatically injected
"""

import httpx
from contextlib import asynccontextmanager
from typing import AsyncIterator

from shared.logging import trace_id_var


class TraceTransport(httpx.AsyncHTTPTransport):
    """
    httpx transport wrapper that injects X-Trace-ID header
    into every outbound request from the current ContextVar.
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
        trace_id = trace_id_var.get("")
        if trace_id:
            request.headers["X-Trace-ID"] = trace_id
        return await super().handle_async_request(request)


@asynccontextmanager
async def traced_client(
    timeout: float = 10.0,
    **kwargs,
) -> AsyncIterator[httpx.AsyncClient]:
    """
    Create an httpx.AsyncClient that auto-injects X-Trace-ID.

    Args:
        timeout: Request timeout in seconds. Default 10.0.
        **kwargs: Additional kwargs passed to httpx.AsyncClient.

    Usage:
        async with traced_client(timeout=5.0) as client:
            resp = await client.get(url)
    """
    transport = TraceTransport()
    async with httpx.AsyncClient(
        transport=transport,
        timeout=timeout,
        **kwargs,
    ) as client:
        yield client

