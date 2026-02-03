from unittest.mock import patch

import pytest

from utils import snmp_validator

pytestmark = [pytest.mark.unit]


@pytest.fixture(scope="session", autouse=True)
async def setup_delivery_tables():
    yield


def test_block_link_local():
    result = snmp_validator.validate_snmp_host("169.254.10.5")
    assert result.valid is False
    assert "blocked network" in result.error.lower()


def test_block_multicast():
    result = snmp_validator.validate_snmp_host("224.0.0.1")
    assert result.valid is False
    assert "blocked network" in result.error.lower()


def test_port_below_range():
    result = snmp_validator.validate_snmp_host("8.8.8.8", port=0)
    assert result.valid is False
    assert "invalid port" in result.error.lower()


def test_port_above_range():
    result = snmp_validator.validate_snmp_host("8.8.8.8", port=65536)
    assert result.valid is False
    assert "invalid port" in result.error.lower()


def test_valid_port_162():
    result = snmp_validator.validate_snmp_host("8.8.8.8", port=162)
    assert result.valid is True


def test_hostname_resolves_to_private():
    with patch(
        "utils.snmp_validator.socket.getaddrinfo",
        return_value=[(0, 0, 0, "", ("10.0.0.9", 162))],
    ):
        result = snmp_validator.validate_snmp_host("example.com", port=162)
    assert result.valid is False
    assert "blocked network" in result.error.lower() or "private" in result.error.lower()


def test_empty_host():
    with patch("utils.snmp_validator.socket.getaddrinfo", side_effect=snmp_validator.socket.gaierror("fail")):
        result = snmp_validator.validate_snmp_host("", port=162)
    assert result.valid is False
    assert "dns resolution failed" in result.error.lower()


def test_block_localhost_hostname():
    result = snmp_validator.validate_snmp_host("localhost", port=162)
    assert result.valid is False
    assert "blocked hostname" in result.error.lower()


def test_block_metadata_hostname():
    result = snmp_validator.validate_snmp_host("metadata.google.internal", port=162)
    assert result.valid is False
    assert "metadata" in result.error.lower()


def test_empty_addr_info():
    with patch("utils.snmp_validator.socket.getaddrinfo", return_value=[]):
        result = snmp_validator.validate_snmp_host("example.com", port=162)
    assert result.valid is False
    assert "could not resolve" in result.error.lower()


def test_dns_resolution_failure():
    with patch("utils.snmp_validator.socket.getaddrinfo", side_effect=snmp_validator.socket.gaierror("boom")):
        result = snmp_validator.validate_snmp_host("example.com", port=162)
    assert result.valid is False
    assert "dns resolution failed" in result.error.lower()


def test_is_snmp_host_allowed():
    with patch("utils.snmp_validator.socket.getaddrinfo", return_value=[(0, 0, 0, "", ("8.8.8.8", 162))]):
        assert snmp_validator.is_snmp_host_allowed("example.com", port=162) is True
