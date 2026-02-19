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
        sim_status: str | None = None,  # active, suspended, deactivated
        network_status: str | None = None,  # connected, disconnected
        ip_address: str | None = None,
        network_type: str | None = None,  # 4G, LTE-M, NB-IoT
        last_connection: str | None = None,  # ISO timestamp
        signal_strength: int | None = None,  # 0-100
        raw: dict | None = None,  # Full carrier response
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
        raise NotImplementedError

    @abstractmethod
    async def get_usage(self, carrier_device_id: str) -> CarrierUsageInfo:
        """Get data usage for current billing cycle."""
        raise NotImplementedError

    @abstractmethod
    async def activate_sim(self, carrier_device_id: str) -> bool:
        """Activate a SIM card."""
        raise NotImplementedError

    @abstractmethod
    async def suspend_sim(self, carrier_device_id: str) -> bool:
        """Suspend a SIM card (keeps data, stops traffic)."""
        raise NotImplementedError

    @abstractmethod
    async def deactivate_sim(self, carrier_device_id: str) -> bool:
        """Deactivate a SIM card (permanent)."""
        raise NotImplementedError

    @abstractmethod
    async def send_sms(self, carrier_device_id: str, message: str) -> bool:
        """Send SMS to device (for wake-up or reset trigger)."""
        raise NotImplementedError

    @abstractmethod
    async def get_network_diagnostics(self, carrier_device_id: str) -> dict[str, Any]:
        """Get detailed network diagnostics (carrier-specific)."""
        raise NotImplementedError

    async def get_bulk_usage(self, carrier_device_ids: list[str]) -> dict[str, CarrierUsageInfo]:
        """Get usage for multiple devices in one call.

        Default behavior: call get_usage() per device and return a map.
        """
        results: dict[str, CarrierUsageInfo] = {}
        for device_id in carrier_device_ids:
            try:
                results[device_id] = await self.get_usage(device_id)
            except Exception:
                logger.warning("Bulk usage: failed for device %s", device_id)
        return results

    async def claim_sim(self, iccid: str, plan_id: int | None = None) -> dict:
        """Claim/provision a new SIM card. Returns carrier device info."""
        raise NotImplementedError

    async def list_plans(self) -> list[dict]:
        """List available data plans from the carrier."""
        raise NotImplementedError


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
            params={"apikey": self.api_key},
            timeout=30.0,
        )

    async def get_device_info(self, carrier_device_id: str) -> CarrierDeviceInfo:
        resp = await self.client.get(f"/devices/{carrier_device_id}")
        resp.raise_for_status()
        data = resp.json().get("data", {})
        links = data.get("links", {}).get("cellular", [])
        link = links[0] if links else {}
        last_session = data.get("lastsession", {})

        # Map Hologram states to our enum
        hologram_state = (data.get("state") or "").lower()
        state_map = {"live": "active", "paused": "suspended", "deactivated": "deactivated"}
        sim_status = state_map.get(hologram_state, hologram_state or None)

        # Infer network status from last session
        network_status = "connected" if last_session.get("active") else "disconnected"

        return CarrierDeviceInfo(
            carrier_device_id=carrier_device_id,
            iccid=link.get("sim"),
            sim_status=sim_status,
            network_status=network_status,
            ip_address=last_session.get("ip"),
            network_type=link.get("networktype"),
            last_connection=link.get("last_connect_time"),
            raw=data,
        )

    async def get_usage(self, carrier_device_id: str) -> CarrierUsageInfo:
        resp = await self.client.get("/usage/data", params={"deviceid": carrier_device_id})
        resp.raise_for_status()
        records = resp.json().get("data", [])
        total_bytes = sum(r.get("bytes", 0) for r in records)
        return CarrierUsageInfo(
            carrier_device_id=carrier_device_id,
            data_used_bytes=total_bytes,
            sessions=records,
            raw={"records": records},
        )

    async def activate_sim(self, carrier_device_id: str) -> bool:
        resp = await self.client.post(f"/devices/{carrier_device_id}/state", json={"state": "live"})
        return resp.status_code == 200

    async def suspend_sim(self, carrier_device_id: str) -> bool:
        resp = await self.client.post(f"/devices/{carrier_device_id}/state", json={"state": "pause"})
        return resp.status_code == 200

    async def deactivate_sim(self, carrier_device_id: str) -> bool:
        resp = await self.client.post(
            f"/devices/{carrier_device_id}/state",
            json={"state": "deactivate"},
        )
        return resp.status_code == 200

    async def send_sms(self, carrier_device_id: str, message: str) -> bool:
        resp = await self.client.post(
            "/sms/incoming",
            json={"deviceid": int(carrier_device_id), "body": message, "fromnumber": "system"},
        )
        return resp.status_code == 200

    async def get_network_diagnostics(self, carrier_device_id: str) -> dict[str, Any]:
        resp = await self.client.get(f"/devices/{carrier_device_id}")
        resp.raise_for_status()
        device_data = resp.json().get("data", {})

        link_data: Any = {}
        try:
            link_resp = await self.client.get("/links/cellular", params={"deviceid": carrier_device_id})
            if link_resp.status_code == 200:
                link_data = link_resp.json().get("data", [])
        except Exception:
            pass  # Non-critical; return device data alone

        return {
            "device": device_data,
            "cellular_links": link_data,
        }

    async def get_bulk_usage(self, carrier_device_ids: list[str]) -> dict[str, CarrierUsageInfo]:
        """Fetch usage for all devices in the org in a single API call."""
        if not self.account_id:
            return await super().get_bulk_usage(carrier_device_ids)

        resp = await self.client.get("/usage/data", params={"orgid": self.account_id})
        resp.raise_for_status()
        records = resp.json().get("data", [])

        by_device: dict[str, list[dict]] = {}
        for r in records:
            did = str(r.get("deviceid", ""))
            if did in carrier_device_ids:
                by_device.setdefault(did, []).append(r)

        results: dict[str, CarrierUsageInfo] = {}
        for did in carrier_device_ids:
            device_records = by_device.get(did, [])
            total_bytes = sum(r.get("bytes", 0) for r in device_records)
            results[did] = CarrierUsageInfo(
                carrier_device_id=did,
                data_used_bytes=total_bytes,
                sessions=device_records,
                raw={"records": device_records},
            )
        return results

    async def claim_sim(self, iccid: str, plan_id: int | None = None) -> dict:
        body: dict[str, Any] = {"sim": iccid}
        if plan_id:
            body["plan"] = plan_id
        resp = await self.client.post(f"/links/cellular/sim_{iccid}/claim", json=body)
        resp.raise_for_status()
        return resp.json().get("data", {})

    async def list_plans(self) -> list[dict]:
        params: dict[str, Any] = {}
        if self.account_id:
            params["orgid"] = self.account_id
        resp = await self.client.get("/plans", params=params)
        resp.raise_for_status()
        return resp.json().get("data", [])


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

    async def get_network_diagnostics(self, carrier_device_id: str) -> dict[str, Any]:
        resp = await self.client.get(f"/sims/{carrier_device_id}/connectivity")
        if resp.status_code == 200:
            return resp.json()
        return {}

    async def claim_sim(self, iccid: str, plan_id: int | None = None) -> dict:
        # 1NCE SIMs are pre-provisioned; no claim flow needed.
        return {"iccid": iccid, "note": "1NCE SIMs are pre-provisioned"}

    async def list_plans(self) -> list[dict]:
        # 1NCE has a single flat-rate plan; not queryable via API.
        return []


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

    kwargs: dict[str, Any] = {
        "api_key": integration.get("api_key", ""),
    }

    if carrier == "hologram":
        kwargs["account_id"] = integration.get("account_id")
    if integration.get("api_base_url"):
        kwargs["base_url"] = integration["api_base_url"]

    return provider_cls(**kwargs)

