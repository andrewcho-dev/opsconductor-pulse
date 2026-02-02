"""SNMP destination address validation."""

import socket
import ipaddress
from typing import Optional
from dataclasses import dataclass

BLOCKED_NETWORKS = [
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.168.0.0/16"),
    ipaddress.ip_network("127.0.0.0/8"),
    ipaddress.ip_network("169.254.0.0/16"),
    ipaddress.ip_network("0.0.0.0/8"),
    ipaddress.ip_network("100.64.0.0/10"),
    ipaddress.ip_network("224.0.0.0/4"),
    ipaddress.ip_network("240.0.0.0/4"),
    ipaddress.ip_network("::1/128"),
    ipaddress.ip_network("fc00::/7"),
    ipaddress.ip_network("fe80::/10"),
]

BLOCKED_HOSTNAMES = ["localhost", "localhost.localdomain"]
BLOCKED_METADATA_HOSTS = ["metadata.google.internal", "169.254.169.254"]


@dataclass
class SNMPValidationResult:
    """Result of SNMP address validation."""

    valid: bool
    error: Optional[str] = None
    resolved_ip: Optional[str] = None


def validate_snmp_host(host: str, port: int = 162) -> SNMPValidationResult:
    """Validate SNMP destination host."""
    if not 1 <= port <= 65535:
        return SNMPValidationResult(valid=False, error=f"Invalid port: {port}")

    host_lower = host.lower().strip()
    if host_lower in BLOCKED_HOSTNAMES:
        return SNMPValidationResult(valid=False, error=f"Blocked hostname: {host}")

    if host_lower in BLOCKED_METADATA_HOSTS:
        return SNMPValidationResult(valid=False, error=f"Blocked metadata endpoint: {host}")

    try:
        ip = ipaddress.ip_address(host)
        return _validate_ip(ip, host)
    except ValueError:
        pass

    try:
        addr_info = socket.getaddrinfo(host, port, socket.AF_UNSPEC, socket.SOCK_DGRAM)
        if not addr_info:
            return SNMPValidationResult(valid=False, error=f"Could not resolve: {host}")

        for family, socktype, proto, canonname, sockaddr in addr_info:
            ip_str = sockaddr[0]
            try:
                ip = ipaddress.ip_address(ip_str)
                result = _validate_ip(ip, host)
                if not result.valid:
                    return result
            except ValueError:
                continue

        return SNMPValidationResult(valid=True, resolved_ip=addr_info[0][4][0])

    except socket.gaierror as e:
        return SNMPValidationResult(valid=False, error=f"DNS resolution failed: {e}")
    except Exception as e:
        return SNMPValidationResult(valid=False, error=str(e))


def _validate_ip(ip, original_host: str) -> SNMPValidationResult:
    """Validate a resolved IP address."""
    for network in BLOCKED_NETWORKS:
        if ip in network:
            return SNMPValidationResult(
                valid=False,
                error=f"IP {ip} is in blocked network {network}",
            )

    if ip.is_private:
        return SNMPValidationResult(valid=False, error=f"IP {ip} is private")
    if ip.is_loopback:
        return SNMPValidationResult(valid=False, error=f"IP {ip} is loopback")
    if ip.is_link_local:
        return SNMPValidationResult(valid=False, error=f"IP {ip} is link-local")
    if ip.is_multicast:
        return SNMPValidationResult(valid=False, error=f"IP {ip} is multicast")

    return SNMPValidationResult(valid=True, resolved_ip=str(ip))


def is_snmp_host_allowed(host: str, port: int = 162) -> bool:
    """Simple boolean check if SNMP host is allowed."""
    return validate_snmp_host(host, port).valid
