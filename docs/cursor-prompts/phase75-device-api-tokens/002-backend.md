# Prompt 002 — Backend: Device API Token endpoints

Read `services/ui_iot/routes/customer.py` fully.

Add three endpoints to the customer router:

### GET /customer/devices/{device_id}/tokens
List non-revoked tokens for a device.

Returns list of:
```json
{
  "id": "uuid",
  "client_id": "string",
  "label": "string",
  "created_at": "iso8601",
  "revoked_at": null
}
```
(never return token_hash)

### DELETE /customer/devices/{device_id}/tokens/{token_id}
Revoke a token: set `revoked_at = now()`. Returns 204.
Return 404 if token not found or already revoked.

### POST /customer/devices/{device_id}/tokens/rotate
Generate a new MQTT credential pair:
- new `client_id` = `f"{tenant_id[:8]}-{device_id[:8]}-{uuid4().hex[:8]}"`
- new `password` = `secrets.token_urlsafe(32)`
- store `token_hash` = bcrypt hash using `passlib.hash.bcrypt.hash(password)`
- label = body.label (default "rotated")
- revoke ALL existing non-revoked tokens for this device first

Returns 201:
```json
{
  "client_id": "...",
  "password": "...",
  "broker_url": "..."
}
```
(raw password returned once, never stored)

Add `passlib[bcrypt]` to `services/ui_iot/requirements.txt` if not present.

## Acceptance Criteria
- [ ] GET /customer/devices/{id}/tokens returns list
- [ ] DELETE revokes token
- [ ] POST /rotate returns new credentials once
- [ ] passlib in requirements.txt
