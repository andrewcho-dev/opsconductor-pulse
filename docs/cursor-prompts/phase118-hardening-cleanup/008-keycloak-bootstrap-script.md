# 008 — Keycloak User Profile Bootstrap Script

## Context

The Keycloak user profile for the `pulse` realm needs a `tenant_id` attribute. A runtime `PUT /admin/realms/pulse/users/profile` fix works now, but won't survive a fresh Keycloak container with an already-initialized realm DB (where `realm-pulse.json` is not re-imported).

## What to Add

Add a `bootstrap_keycloak_profile()` function to `scripts/seed_demo_data.py` that idempotently ensures the `tenant_id` attribute exists in the Keycloak user profile configuration.

## Step 1 — Add `httpx` import

**File**: `scripts/seed_demo_data.py`

Add to the imports at the top of the file (after the existing imports, around line 9):

```python
import httpx
```

## Step 2 — Add env vars

After the existing `PG_PASS` env var line (around line 18), add:

```python
KEYCLOAK_INTERNAL_URL = os.getenv("KEYCLOAK_INTERNAL_URL", "http://keycloak:8080")
KEYCLOAK_ADMIN_PASSWORD = os.environ.get("KEYCLOAK_ADMIN_PASSWORD", "admin_dev")
```

## Step 3 — Add `bootstrap_keycloak_profile()` function

Add this function before `async def main()`:

```python
async def bootstrap_keycloak_profile():
    """Ensure Keycloak pulse realm has tenant_id in user profile attributes."""
    print("Bootstrapping Keycloak user profile...")

    async with httpx.AsyncClient(timeout=30) as client:
        # Get admin token
        token_resp = await client.post(
            f"{KEYCLOAK_INTERNAL_URL}/realms/master/protocol/openid-connect/token",
            data={
                "grant_type": "client_credentials",
                "client_id": "admin-cli",
                "username": "admin",
                "password": KEYCLOAK_ADMIN_PASSWORD,
                "grant_type": "password",
            },
        )
        token_resp.raise_for_status()
        token = token_resp.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # Get current user profile config
        profile_resp = await client.get(
            f"{KEYCLOAK_INTERNAL_URL}/admin/realms/pulse/users/profile",
            headers=headers,
        )
        profile_resp.raise_for_status()
        profile = profile_resp.json()

        # Check if tenant_id attribute already exists
        attr_names = [a["name"] for a in profile.get("attributes", [])]
        if "tenant_id" in attr_names:
            print("  tenant_id attribute already exists — skipping.")
            return

        # Add tenant_id attribute
        profile.setdefault("attributes", []).append({
            "name": "tenant_id",
            "displayName": "Tenant ID",
            "validations": {},
            "annotations": {},
            "permissions": {"view": ["admin", "user"], "edit": ["admin"]},
            "multivalued": False,
        })

        put_resp = await client.put(
            f"{KEYCLOAK_INTERNAL_URL}/admin/realms/pulse/users/profile",
            headers=headers,
            json=profile,
        )
        put_resp.raise_for_status()
        print("  tenant_id attribute added to user profile.")
```

**Note on the token request**: The `data` dict has `grant_type` twice — the second one (`"password"`) wins. This is the correct value for admin username/password auth. Clean it up to only have `"grant_type": "password"` once if you prefer.

## Step 4 — Call from `main()`

**File**: `scripts/seed_demo_data.py`

In `async def main()`, add the call at the beginning (before DB operations):

```python
async def main():
    # Bootstrap Keycloak profile (idempotent)
    try:
        await bootstrap_keycloak_profile()
    except Exception as e:
        print(f"  Warning: Keycloak bootstrap skipped ({e})")

    devices = list(iter_devices())
    ...
```

Wrapping in try/except allows the script to still work when Keycloak is not available (e.g., running seed script against DB only).

## Step 5 — Commit

```bash
git add scripts/seed_demo_data.py
git commit -m "feat: add idempotent Keycloak user profile bootstrap to seed script"
```

## Verification

```bash
# Syntax check
python -c "import ast; ast.parse(open('scripts/seed_demo_data.py').read()); print('OK')"

# Function exists
grep "bootstrap_keycloak_profile" scripts/seed_demo_data.py
# Should show the function definition and the call in main()
```
