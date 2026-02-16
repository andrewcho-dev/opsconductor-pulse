#!/usr/bin/env python3
import json
import os
import urllib.request
import urllib.error

TENANT_ID = os.getenv("TENANT_ID", "tenant-a")
SITE_PREFIX = os.getenv("SITE_PREFIX", "sim-site")
SITES_COUNT = int(os.getenv("SITES_COUNT", "5"))
DEVICE_COUNT = int(os.getenv("DEVICE_COUNT", "100"))

PROVISION_API_URL = os.getenv("PROVISION_API_URL", "http://localhost:8081")
PROVISION_ADMIN_KEY = os.environ["PROVISION_ADMIN_KEY"]


def generate_devices():
    devices = []
    for idx in range(1, DEVICE_COUNT + 1):
        site_id = f"{SITE_PREFIX}-{(idx % SITES_COUNT) + 1}"
        device_id = f"{site_id}-dev-{idx:05d}"
        devices.append((TENANT_ID, site_id, device_id))
    return devices


def provision_device(api_url, admin_key, tenant_id, device_id, site_id):
    payload = json.dumps({"tenant_id": tenant_id, "device_id": device_id, "site_id": site_id}).encode()
    req = urllib.request.Request(
        f"{api_url.rstrip('/')}/api/admin/devices",
        data=payload,
        headers={"Content-Type": "application/json", "X-Admin-Key": admin_key},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=10) as resp:
        body = json.loads(resp.read().decode())
    activation_code = body["activation_code"]
    activate_payload = json.dumps(
        {"tenant_id": tenant_id, "device_id": device_id, "activation_code": activation_code}
    ).encode()
    activate_req = urllib.request.Request(
        f"{api_url.rstrip('/')}/api/device/activate",
        data=activate_payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(activate_req, timeout=10) as resp:
        activate_body = json.loads(resp.read().decode())
    return activate_body["provision_token"]


def main():
    devices = generate_devices()
    print(f"Provisioning {len(devices)} devices for tenant={TENANT_ID}")
    ok = 0
    failed = 0
    for tenant_id, site_id, device_id in devices:
        try:
            provision_device(PROVISION_API_URL, PROVISION_ADMIN_KEY, tenant_id, device_id, site_id)
            ok += 1
        except Exception:
            failed += 1
    print(f"Done. ok={ok} failed={failed}")


if __name__ == "__main__":
    main()
