import asyncio
import ipaddress
import os
import socket
from urllib.parse import urlparse


BLOCKED_NETWORKS = [
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.168.0.0/16"),
    ipaddress.ip_network("127.0.0.0/8"),
    ipaddress.ip_network("169.254.0.0/16"),
    ipaddress.ip_network("0.0.0.0/8"),
    ipaddress.ip_network("::1/128"),
    ipaddress.ip_network("fc00::/7"),
    ipaddress.ip_network("fe80::/10"),
]


def is_blocked_ip(ip_str: str) -> bool:
    try:
        ip = ipaddress.ip_address(ip_str)
        return any(ip in network for network in BLOCKED_NETWORKS)
    except ValueError:
        return False


async def resolve_hostname(hostname: str, timeout: float = 5.0) -> list[str]:
    loop = asyncio.get_event_loop()
    try:
        result = await asyncio.wait_for(loop.getaddrinfo(hostname, None), timeout=timeout)
        return [info[4][0] for info in result]
    except (asyncio.TimeoutError, socket.gaierror):
        return []


async def validate_webhook_url(url: str, allow_http: bool | None = None) -> tuple[bool, str | None]:
    if allow_http is None:
        allow_http = os.getenv("ALLOW_HTTP_WEBHOOKS", "false").lower() == "true"

    try:
        parsed = urlparse(url)
    except Exception:
        return False, "Invalid URL format"

    if not parsed.scheme or not parsed.netloc:
        return False, "Invalid URL format"

    scheme = parsed.scheme.lower()
    if allow_http:
        if scheme not in ("http", "https"):
            return False, "Only HTTPS URLs are allowed"
    else:
        if scheme != "https":
            return False, "Only HTTPS URLs are allowed"

    hostname = parsed.hostname or ""
    lowered = hostname.lower()
    if lowered in {"localhost"} or lowered.endswith(".local") or lowered.endswith(".internal") or lowered.endswith(".localhost"):
        return False, "Internal hostnames are not allowed"
    if lowered in {"metadata.google.internal"}:
        return False, "Cloud metadata endpoints are not allowed"

    if is_blocked_ip(hostname):
        return False, "Private IP addresses are not allowed"
    if hostname in {"169.254.169.254", "169.254.170.2"}:
        return False, "Cloud metadata endpoints are not allowed"

    resolved = await resolve_hostname(hostname)
    if not resolved:
        return False, "Invalid URL format"
    for ip_str in resolved:
        if ip_str in {"169.254.169.254", "169.254.170.2"}:
            return False, "Cloud metadata endpoints are not allowed"
        if is_blocked_ip(ip_str):
            return False, "Hostname resolves to blocked IP address"

    return True, None
