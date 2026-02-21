# Task 002 — Carrier Service Abstraction

## File

Create `services/ui_iot/services/carrier_service.py`

## Design

A pluggable carrier service with a provider interface. Each MVNO carrier implements the interface. The service routes calls to the correct provider based on the carrier_integration record.

## Interface

```python
"""Carrier service abstraction for MVNO/IoT connectivity platform integration."""

import logging
from abc import ABC, abstractmethod
from typing import Any
import httpx

logger = logging.getLogger(__name__)


class CarrierDeviceInfo:
    """Standardized device info returned from any carrier."""
    def __init__(
        self,
        carrier_device_id: str,
        iccid: str | None = None,
        sim_status: str | None = None,        # active, suspended, deactivated
        network_status: str | None = None,     # connected, disconnected
        ip_address: str | None = None,
        network_type: str | None = None,       # 4G, LTE-M, NB-IoT
        last_connection: str | None = None,    # ISO timestamp
        signal_strength: int | None = None,    # 0-100
        raw: dict | None = None,               # Full carrier response
    ):
        self.carrier_device_id = carrier_device_id
        self.iccid = iccid
        self.sim_status = sim_status
        self.network_status = network_status
        self.ip_address = ip_address
        self.network_type = network_type
        self.last_connection = last_connection
        self.signal_strength = signal_strength
        self.raw = raw or {}


class CarrierUsageInfo:
    """Standardized data usage info."""
    def __init__(
        self,
        carrier_device_id: str,
        data_used_bytes: int = 0,
        data_limit_bytes: int | None = None,
        billing_cycle_start: str | None = None,
        billing_cycle_end: str | None = None,
        sms_count: int = 0,
        sessions: list[dict] | None = None,
        raw: dict | None = None,
    ):
        self.carrier_device_id = carrier_device_id
        self.data_used_bytes = data_used_bytes
        self.data_limit_bytes = data_limit_bytes
        self.billing_cycle_start = billing_cycle_start
        self.billing_cycle_end = billing_cycle_end
        self.sms_count = sms_count
        self.sessions = sessions or []
        self.raw = raw or {}


class CarrierProvider(ABC):
    """Abstract base class for carrier API providers."""

    @abstractmethod
    async def get_device_info(self, carrier_device_id: str) -> CarrierDeviceInfo:
        """Get device/SIM status and connection info."""
        ...

    @abstractmethod
    async def get_usage(self, carrier_device_id: str) -> CarrierUsageInfo:
        """Get data usage for current billing cycle."""
        ...

    @abstractmethod
    async def activate_sim(self, carrier_device_id: str) -> bool:
        """Activate a SIM card."""
        ...

    @abstractmethod
    async def suspend_sim(self, carrier_device_id: str) -> bool:
        """Suspend a SIM card (keeps data, stops traffic)."""
        ...

    @abstractmethod
    async def deactivate_sim(self, carrier_device_id: str) -> bool:
        """Deactivate a SIM card (permanent)."""
        ...

    @abstractmethod
    async def send_sms(self, carrier_device_id: str, message: str) -> bool:
        """Send SMS to device (for wake-up or reset trigger)."""
        ...

    @abstractmethod
    async def get_network_diagnostics(self, carrier_device_id: str) -> dict[str, Any]:
        """Get detailed network diagnostics (carrier-specific)."""
        ...


class HologramProvider(CarrierProvider):
    """Hologram (hologram.io) carrier API integration.

    API docs: https://www.hologram.io/references/http-endpoints
    """

    def __init__(self, api_key: str, account_id: str | None = None, base_url: str | None = None):
        self.api_key = api_key
        self.account_id = account_id
        self.base_url = base_url or "https://dashboard.hologram.io/api/1"
        self.client = httpx.AsyncClient(
            base_url=self.base_url,
            headers={"apikey": self.api_key},
            timeout=30.0,
        )

    async def get_device_info(self, carrier_device_id: str) -> CarrierDeviceInfo:
        resp = await self.client.get(f"/devices/{carrier_device_id}")
        resp.raise_for_status()
        data = resp.json().get("data", {})
        links = data.get("links", {}).get("cellular", [])
        link = links[0] if links else {}
        return CarrierDeviceInfo(
            carrier_device_id=carrier_device_id,
            iccid=link.get("sim"),
            sim_status=data.get("state"),
            network_status="connected" if link.get("last_connect_time") else "disconnected",
            last_connection=link.get("last_connect_time"),
            raw=data,
        )

    async def get_usage(self, carrier_device_id: str) -> CarrierUsageInfo:
        resp = await self.client.get(f"/devices/{carrier_device_id}/usage")
        resp.raise_for_status()
        data = resp.json().get("data", {})
        return CarrierUsageInfo(
            carrier_device_id=carrier_device_id,
            data_used_bytes=data.get("data", 0),
            raw=data,
        )

    async def activate_sim(self, carrier_device_id: str) -> bool:
        resp = await self.client.post(f"/devices/{carrier_device_id}/activate")
        return resp.status_code == 200

    async def suspend_sim(self, carrier_device_id: str) -> bool:
        resp = await self.client.post(f"/devices/{carrier_device_id}/pause")
        return resp.status_code == 200

    async def deactivate_sim(self, carrier_device_id: str) -> bool:
        resp = await self.client.post(f"/devices/{carrier_device_id}/deactivate")
        return resp.status_code == 200

    async def send_sms(self, carrier_device_id: str, message: str) -> bool:
        resp = await self.client.post(
            f"/sms/incoming",
            json={"deviceid": int(carrier_device_id), "body": message, "fromNumber": "system"},
        )
        return resp.status_code == 200

    async def get_network_diagnostics(self, carrier_device_id: str) -> dict:
        resp = await self.client.get(f"/devices/{carrier_device_id}")
        resp.raise_for_status()
        return resp.json().get("data", {})


class OneNCEProvider(CarrierProvider):
    """1NCE carrier API integration.

    API docs: https://1nce.com/en/developer-hub
    """

    def __init__(self, api_key: str, base_url: str | None = None):
        self.base_url = base_url or "https://api.1nce.com/management/v1"
        self.client = httpx.AsyncClient(
            base_url=self.base_url,
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=30.0,
        )

    async def get_device_info(self, carrier_device_id: str) -> CarrierDeviceInfo:
        # 1NCE uses ICCID as the device ID
        resp = await self.client.get(f"/sims/{carrier_device_id}")
        resp.raise_for_status()
        data = resp.json()
        return CarrierDeviceInfo(
            carrier_device_id=carrier_device_id,
            iccid=data.get("iccid"),
            sim_status=data.get("status"),
            ip_address=data.get("ip_address"),
            raw=data,
        )

    async def get_usage(self, carrier_device_id: str) -> CarrierUsageInfo:
        resp = await self.client.get(f"/sims/{carrier_device_id}/quota/data")
        resp.raise_for_status()
        data = resp.json()
        return CarrierUsageInfo(
            carrier_device_id=carrier_device_id,
            data_used_bytes=data.get("volume", 0),
            data_limit_bytes=data.get("total_volume"),
            raw=data,
        )

    async def activate_sim(self, carrier_device_id: str) -> bool:
        resp = await self.client.patch(f"/sims/{carrier_device_id}", json={"status": "Enabled"})
        return resp.status_code == 200

    async def suspend_sim(self, carrier_device_id: str) -> bool:
        resp = await self.client.patch(f"/sims/{carrier_device_id}", json={"status": "Disabled"})
        return resp.status_code == 200

    async def deactivate_sim(self, carrier_device_id: str) -> bool:
        return await self.suspend_sim(carrier_device_id)

    async def send_sms(self, carrier_device_id: str, message: str) -> bool:
        resp = await self.client.post(
            f"/sims/{carrier_device_id}/sms",
            json={"payload": message},
        )
        return resp.status_code == 200

    async def get_network_diagnostics(self, carrier_device_id: str) -> dict:
        resp = await self.client.get(f"/sims/{carrier_device_id}/connectivity")
        if resp.status_code == 200:
            return resp.json()
        return {}


# ─── Provider Registry ─────────────────────────────────

CARRIER_PROVIDERS: dict[str, type[CarrierProvider]] = {
    "hologram": HologramProvider,
    "1nce": OneNCEProvider,
}


def get_carrier_provider(integration: dict) -> CarrierProvider | None:
    """Create a carrier provider instance from an integration record."""
    carrier = integration.get("carrier_name")
    provider_cls = CARRIER_PROVIDERS.get(carrier)
    if not provider_cls:
        logger.warning("Unknown carrier provider: %s", carrier)
        return None

    kwargs = {
        "api_key": integration.get("api_key", ""),
    }

    if carrier == "hologram":
        kwargs["account_id"] = integration.get("account_id")
    if integration.get("api_base_url"):
        kwargs["base_url"] = integration["api_base_url"]

    return provider_cls(**kwargs)
```

## Notes

- The Hologram and 1NCE implementations are based on their public API documentation. The exact endpoints and payloads may need adjustment during testing with real carrier accounts.
- `httpx.AsyncClient` is used for async HTTP calls — it should already be in the project's dependencies. If not, add `httpx` to requirements.
- API keys stored in `carrier_integrations` should be encrypted. For now, they're stored as plain text (same as other secrets in the codebase). A future phase can add encryption.
- New carrier providers can be added by implementing `CarrierProvider` and registering in `CARRIER_PROVIDERS`.

## Verification

```bash
cd services/ui_iot && python3 -c "from services.carrier_service import get_carrier_provider, CARRIER_PROVIDERS; print('Providers:', list(CARRIER_PROVIDERS.keys()))"
```
