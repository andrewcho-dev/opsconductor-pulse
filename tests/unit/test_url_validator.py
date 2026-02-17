from unittest.mock import AsyncMock

import pytest

from utils import url_validator

pytestmark = [pytest.mark.unit]


@pytest.fixture(scope="session", autouse=True)
async def setup_delivery_tables():
    yield


@pytest.mark.asyncio
async def test_block_127_0_0_1():
    valid, error = await url_validator.validate_webhook_url("https://127.0.0.1/hook")
    assert valid is False
    assert "not allowed" in error.lower()


@pytest.mark.asyncio
async def test_block_10_x_x_x():
    valid, error = await url_validator.validate_webhook_url("https://10.1.2.3/hook")
    assert valid is False
    assert "not allowed" in error.lower()


@pytest.mark.asyncio
async def test_block_172_16_x_x():
    valid, error = await url_validator.validate_webhook_url("https://172.16.5.5/hook")
    assert valid is False
    assert "not allowed" in error.lower()


@pytest.mark.asyncio
async def test_block_192_168_x_x():
    valid, error = await url_validator.validate_webhook_url("https://192.168.1.2/hook")
    assert valid is False
    assert "not allowed" in error.lower()


@pytest.mark.asyncio
async def test_block_169_254_metadata():
    valid, error = await url_validator.validate_webhook_url("https://169.254.169.254/hook")
    assert valid is False
    assert error is not None


@pytest.mark.asyncio
async def test_block_0_0_0_0():
    valid, error = await url_validator.validate_webhook_url("https://0.0.0.0/hook")
    assert valid is False
    assert "not allowed" in error.lower()


@pytest.mark.asyncio
async def test_block_localhost():
    valid, error = await url_validator.validate_webhook_url("https://localhost/hook")
    assert valid is False
    assert "internal hostnames" in error.lower()


@pytest.mark.asyncio
async def test_allow_public_ip(monkeypatch):
    monkeypatch.setattr(url_validator, "resolve_hostname", AsyncMock(return_value=["8.8.8.8"]))
    valid, error = await url_validator.validate_webhook_url("https://8.8.8.8/hook")
    assert valid is True
    assert error is None


@pytest.mark.asyncio
async def test_allow_public_domain(monkeypatch):
    monkeypatch.setattr(url_validator, "resolve_hostname", AsyncMock(return_value=["93.184.216.34"]))
    valid, error = await url_validator.validate_webhook_url("https://example.com/hook")
    assert valid is True
    assert error is None


@pytest.mark.asyncio
async def test_valid_https_custom_port(monkeypatch):
    monkeypatch.setattr(url_validator, "resolve_hostname", AsyncMock(return_value=["93.184.216.34"]))
    ok, err = await url_validator.validate_webhook_url("https://webhook.example.com:8443/hook")
    assert ok is True
    assert err is None


@pytest.mark.asyncio
async def test_block_scheme_file():
    valid, error = await url_validator.validate_webhook_url("file:///etc/passwd")
    assert valid is False
    assert "invalid url format" in error.lower() or "only https" in error.lower()


@pytest.mark.asyncio
async def test_block_scheme_ftp():
    valid, error = await url_validator.validate_webhook_url("ftp://example.com/hook")
    assert valid is False
    assert "only https" in error.lower()


@pytest.mark.asyncio
async def test_http_blocked_by_default(monkeypatch):
    monkeypatch.setattr(url_validator, "resolve_hostname", AsyncMock(return_value=["93.184.216.34"]))
    ok, err = await url_validator.validate_webhook_url("http://example.com/webhook")
    assert ok is False
    assert err is not None
    assert "https" in err.lower() or "only https" in err.lower()


@pytest.mark.asyncio
async def test_http_allowed_when_flag_set(monkeypatch):
    monkeypatch.setattr(url_validator, "resolve_hostname", AsyncMock(return_value=["93.184.216.34"]))
    ok, err = await url_validator.validate_webhook_url("http://example.com/webhook", allow_http=True)
    assert ok is True
    assert err is None


@pytest.mark.asyncio
async def test_reject_empty_url():
    valid, error = await url_validator.validate_webhook_url("")
    assert valid is False
    assert "invalid url format" in error.lower()


@pytest.mark.asyncio
async def test_reject_no_hostname():
    valid, error = await url_validator.validate_webhook_url("https:///hook")
    assert valid is False
    assert "invalid url format" in error.lower()


@pytest.mark.asyncio
async def test_block_dns_rebinding(monkeypatch):
    monkeypatch.setattr(url_validator, "resolve_hostname", AsyncMock(return_value=["10.0.0.5"]))
    valid, error = await url_validator.validate_webhook_url("https://example.com/hook")
    assert valid is False
    assert "blocked ip" in error.lower()


@pytest.mark.asyncio
async def test_block_ipv6_loopback():
    valid, error = await url_validator.validate_webhook_url("https://[::1]/hook")
    assert valid is False
    assert "not allowed" in error.lower()


@pytest.mark.asyncio
async def test_reject_url_too_long(monkeypatch):
    long_url = "https://" + ("a" * 10000) + ".com/hook"

    def _raise(_):
        raise ValueError("too long")

    monkeypatch.setattr(url_validator, "urlparse", _raise)
    valid, error = await url_validator.validate_webhook_url(long_url)
    assert valid is False
    assert "invalid url format" in error.lower()


@pytest.mark.asyncio
async def test_block_internal_hostname_suffix():
    valid, error = await url_validator.validate_webhook_url("https://service.internal/hook")
    assert valid is False
    assert "internal hostnames" in error.lower()


@pytest.mark.asyncio
async def test_block_dot_local():
    ok, err = await url_validator.validate_webhook_url("https://myservice.local/webhook")
    assert ok is False
    assert err is not None


@pytest.mark.asyncio
async def test_block_dot_localhost():
    ok, err = await url_validator.validate_webhook_url("https://example.localhost/webhook")
    assert ok is False
    assert err is not None


@pytest.mark.asyncio
async def test_block_metadata_hostname():
    valid, error = await url_validator.validate_webhook_url("https://metadata.google.internal/hook")
    assert valid is False
    assert "metadata" in error.lower() or "internal hostnames" in error.lower()


@pytest.mark.asyncio
async def test_block_resolved_metadata_ip(monkeypatch):
    monkeypatch.setattr(url_validator, "resolve_hostname", AsyncMock(return_value=["169.254.169.254"]))
    valid, error = await url_validator.validate_webhook_url("https://example.com/hook")
    assert valid is False
    assert "metadata" in error.lower()


@pytest.mark.asyncio
async def test_resolve_hostname_timeout(monkeypatch):
    monkeypatch.setattr(url_validator, "resolve_hostname", AsyncMock(return_value=[]))
    valid, error = await url_validator.validate_webhook_url("https://example.com/hook")
    assert valid is False
    assert "invalid url format" in error.lower()


@pytest.mark.asyncio
async def test_url_with_credentials(monkeypatch):
    monkeypatch.setattr(url_validator, "resolve_hostname", AsyncMock(return_value=["93.184.216.34"]))
    ok, err = await url_validator.validate_webhook_url("https://user:pass@example.com/webhook")
    assert ok is True
    assert err is None


@pytest.mark.asyncio
async def test_allow_http_when_configured(monkeypatch):
    monkeypatch.setenv("ALLOW_HTTP_WEBHOOKS", "true")
    monkeypatch.setattr(url_validator, "resolve_hostname", AsyncMock(return_value=["93.184.216.34"]))
    valid, error = await url_validator.validate_webhook_url("http://example.com/hook")
    assert valid is True
    assert error is None


@pytest.mark.asyncio
async def test_resolve_hostname_success(monkeypatch):
    class DummyLoop:
        async def getaddrinfo(self, hostname, _):
            return [(None, None, None, None, ("8.8.8.8", 0))]

    monkeypatch.setattr(url_validator.asyncio, "get_event_loop", lambda: DummyLoop())
    resolved = await url_validator.resolve_hostname("example.com")
    assert resolved == ["8.8.8.8"]


@pytest.mark.asyncio
async def test_resolve_hostname_gaierror(monkeypatch):
    class DummyLoop:
        async def getaddrinfo(self, hostname, _):
            raise url_validator.socket.gaierror("fail")

    monkeypatch.setattr(url_validator.asyncio, "get_event_loop", lambda: DummyLoop())
    resolved = await url_validator.resolve_hostname("example.com")
    assert resolved == []
