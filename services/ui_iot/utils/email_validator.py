"""Email integration validation."""

import ipaddress
import re
import socket
from dataclasses import dataclass
from typing import Optional

# Reuse blocked networks from SNMP validator
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

# Common disposable email domains to block (optional, can be extended)
BLOCKED_EMAIL_DOMAINS = [
    "mailinator.com",
    "guerrillamail.com",
    "tempmail.com",
    "throwaway.email",
    "10minutemail.com",
]

# Email regex pattern (simplified but effective)
EMAIL_PATTERN = re.compile(
    r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
)


@dataclass
class EmailValidationResult:
    """Result of email validation."""

    valid: bool
    error: Optional[str] = None


@dataclass
class SMTPValidationResult:
    """Result of SMTP host validation."""

    valid: bool
    error: Optional[str] = None
    resolved_ip: Optional[str] = None


def validate_email_address(email: str) -> EmailValidationResult:
    """Validate a single email address."""
    if not email:
        return EmailValidationResult(valid=False, error="Email address is empty")

    email = email.strip().lower()

    if len(email) > 254:
        return EmailValidationResult(valid=False, error="Email address too long")

    if not EMAIL_PATTERN.match(email):
        return EmailValidationResult(valid=False, error="Invalid email format")

    # Extract domain
    try:
        domain = email.split("@")[1]
    except IndexError:
        return EmailValidationResult(valid=False, error="Invalid email format")

    # Check for blocked disposable domains (optional)
    if domain in BLOCKED_EMAIL_DOMAINS:
        return EmailValidationResult(valid=False, error=f"Disposable email domain not allowed: {domain}")

    return EmailValidationResult(valid=True)


def validate_smtp_host(host: str, port: int = 587) -> SMTPValidationResult:
    """Validate SMTP host is not internal/private."""
    if not host:
        return SMTPValidationResult(valid=False, error="SMTP host is empty")

    if not 1 <= port <= 65535:
        return SMTPValidationResult(valid=False, error=f"Invalid port: {port}")

    host_lower = host.lower().strip()

    if host_lower in BLOCKED_HOSTNAMES:
        return SMTPValidationResult(valid=False, error=f"Blocked hostname: {host}")

    # Check if it's an IP address
    try:
        ip = ipaddress.ip_address(host)
        return _validate_ip(ip)
    except ValueError:
        pass

    # Resolve hostname
    try:
        addr_info = socket.getaddrinfo(host, port, socket.AF_UNSPEC, socket.SOCK_STREAM)
        if not addr_info:
            return SMTPValidationResult(valid=False, error=f"Could not resolve: {host}")

        for family, socktype, proto, canonname, sockaddr in addr_info:
            ip_str = sockaddr[0]
            try:
                ip = ipaddress.ip_address(ip_str)
                result = _validate_ip(ip)
                if not result.valid:
                    return result
            except ValueError:
                continue

        return SMTPValidationResult(valid=True, resolved_ip=addr_info[0][4][0])

    except socket.gaierror as e:
        return SMTPValidationResult(valid=False, error=f"DNS resolution failed: {e}")
    except Exception as e:
        return SMTPValidationResult(valid=False, error=str(e))


def _validate_ip(ip) -> SMTPValidationResult:
    """Validate a resolved IP address."""
    for network in BLOCKED_NETWORKS:
        if ip in network:
            return SMTPValidationResult(
                valid=False,
                error=f"IP {ip} is in blocked network {network}",
            )

    if ip.is_private:
        return SMTPValidationResult(valid=False, error=f"IP {ip} is private")
    if ip.is_loopback:
        return SMTPValidationResult(valid=False, error=f"IP {ip} is loopback")
    if ip.is_link_local:
        return SMTPValidationResult(valid=False, error=f"IP {ip} is link-local")
    if ip.is_multicast:
        return SMTPValidationResult(valid=False, error=f"IP {ip} is multicast")

    return SMTPValidationResult(valid=True, resolved_ip=str(ip))


def validate_email_integration(
    smtp_host: str,
    smtp_port: int,
    from_address: str,
    recipients: dict,
) -> EmailValidationResult:
    """Validate complete email integration configuration."""
    # Validate SMTP host
    smtp_result = validate_smtp_host(smtp_host, smtp_port)
    if not smtp_result.valid:
        return EmailValidationResult(valid=False, error=f"SMTP host: {smtp_result.error}")

    # Validate from address
    from_result = validate_email_address(from_address)
    if not from_result.valid:
        return EmailValidationResult(valid=False, error=f"From address: {from_result.error}")

    # Validate recipients
    to_list = recipients.get("to", [])
    cc_list = recipients.get("cc", [])
    bcc_list = recipients.get("bcc", [])

    if not to_list:
        return EmailValidationResult(valid=False, error="At least one recipient required")

    all_recipients = to_list + cc_list + bcc_list

    if len(all_recipients) > 50:
        return EmailValidationResult(valid=False, error="Maximum 50 recipients allowed")

    for email in all_recipients:
        result = validate_email_address(email)
        if not result.valid:
            return EmailValidationResult(valid=False, error=f"Recipient {email}: {result.error}")

    return EmailValidationResult(valid=True)
