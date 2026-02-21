# 001 — Generate All New Secrets

## Goal

Generate cryptographically strong secrets for every credential. Store them
in a temporary file, then apply in subsequent steps.

## Step 1 — Backup Current .env

```bash
cd ~/simcloud/compose
cp .env .env.bak.$(date +%Y%m%d-%H%M%S)
```

## Step 2 — Generate Secrets

Run this on the Docker host (192.168.50.53):

```bash
echo "=== GENERATED SECRETS — $(date) ==="
echo "KEEP THIS OUTPUT SAFE. DELETE AFTER APPLYING."
echo ""
echo "POSTGRES_PASSWORD=$(python3 -c 'import secrets; print(secrets.token_hex(32))')"
echo "ADMIN_KEY=$(python3 -c 'import secrets; print(secrets.token_hex(32))')"
echo "PROVISION_ADMIN_KEY=$(python3 -c 'import secrets; print(secrets.token_hex(32))')"
echo "KEYCLOAK_ADMIN_PASSWORD=$(python3 -c 'import secrets; print(secrets.token_hex(32))')"
echo "KC_DB_USER_PASSWORD=$(python3 -c 'import secrets; print(secrets.token_hex(32))')"
echo "MQTT_ADMIN_PASSWORD=$(python3 -c 'import secrets; print(secrets.token_hex(32))')"
echo "KEYCLOAK_CLIENT_SECRET=$(python3 -c 'import secrets; print(secrets.token_hex(32))')"
```

**Copy this output somewhere safe** (password manager, encrypted note).
You will need these values for the next steps.

## Notes

- `PG_PASS` will be set to the same value as `POSTGRES_PASSWORD` (they
  are the same credential — the Postgres user password).
- Each secret is 64 hex characters (256 bits of entropy).
- Do NOT save the generated secrets to a file on the server. Copy them
  to your local password manager immediately.
- If you lose these values after applying them, you will need to re-rotate.
