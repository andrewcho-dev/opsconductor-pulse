# Task 5: Add Development Certificate Generation Script

## Context

TLS requires certificates. For local development, a self-signed CA and server certificate need to be generated and placed where docker-compose expects them (`./certs/emqx/`). This must be automated via a script and the generated certs must be gitignored.

## Actions

1. Create the directory `scripts/` if it doesn't exist. Create `scripts/generate-dev-certs.sh`:

```bash
#!/bin/bash
# Generate self-signed CA and EMQX server certificate for local development.
# NOT for production use.
set -euo pipefail

CERT_DIR="$(dirname "$0")/../compose/certs/emqx"
mkdir -p "$CERT_DIR"

echo "Generating dev CA..."
openssl genrsa -out "$CERT_DIR/ca.key" 4096
openssl req -new -x509 -days 3650 -key "$CERT_DIR/ca.key" \
  -out "$CERT_DIR/ca.crt" \
  -subj "/CN=OpsConductor-Dev-CA/O=OpsConductor/C=US"

echo "Generating EMQX server cert..."
openssl genrsa -out "$CERT_DIR/server.key" 2048
openssl req -new -key "$CERT_DIR/server.key" \
  -out "$CERT_DIR/server.csr" \
  -subj "/CN=localhost/O=OpsConductor/C=US"
openssl x509 -req -days 365 \
  -in "$CERT_DIR/server.csr" \
  -CA "$CERT_DIR/ca.crt" \
  -CAkey "$CERT_DIR/ca.key" \
  -CAcreateserial \
  -out "$CERT_DIR/server.crt" \
  -extfile <(printf "subjectAltName=DNS:localhost,IP:127.0.0.1")

rm "$CERT_DIR/server.csr"
echo "Certs generated in $CERT_DIR"
echo "Run: docker compose up to start with TLS enabled."
```

2. Make the script executable: `chmod +x scripts/generate-dev-certs.sh`

3. Add the cert directory to `.gitignore`:
   ```
   compose/certs/
   ```

4. Add a note to `compose/.env.example` and/or `docs/development/getting-started.md`:
   ```
   # Generate dev TLS certificates (required for MQTT TLS):
   # bash scripts/generate-dev-certs.sh
   ```

5. Do not commit any `.crt`, `.key`, or `.pem` files.

## Verification

```bash
# Script exists and is executable
ls -la scripts/generate-dev-certs.sh

# Certs dir is gitignored
grep 'compose/certs' .gitignore
```
