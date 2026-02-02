"""Unit tests for SNMP address validator."""

import pytest
from services.ui_iot.utils.snmp_validator import validate_snmp_host, is_snmp_host_allowed

pytestmark = pytest.mark.unit


class TestSNMPAddressValidation:
    """Test SNMP address validation."""

    def test_localhost_blocked(self):
        result = validate_snmp_host("localhost")
        assert not result.valid

    def test_loopback_blocked(self):
        result = validate_snmp_host("127.0.0.1")
        assert not result.valid

    def test_private_10_blocked(self):
        result = validate_snmp_host("10.0.0.1")
        assert not result.valid

    def test_private_172_blocked(self):
        result = validate_snmp_host("172.16.0.1")
        assert not result.valid

    def test_private_192_blocked(self):
        result = validate_snmp_host("192.168.1.1")
        assert not result.valid

    def test_metadata_blocked(self):
        result = validate_snmp_host("169.254.169.254")
        assert not result.valid

    def test_invalid_port(self):
        result = validate_snmp_host("8.8.8.8", port=0)
        assert not result.valid

    def test_public_ip_allowed(self):
        result = validate_snmp_host("8.8.8.8")
        assert result.valid

    def test_is_snmp_host_allowed_helper(self):
        assert not is_snmp_host_allowed("localhost")
        assert is_snmp_host_allowed("8.8.8.8")
