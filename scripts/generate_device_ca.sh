#!/usr/bin/env bash
set -euo pipefail

# Generate a Device CA for signing IoT device client certificates.
# Output: compose/mosquitto/certs/device-ca.crt and device-ca.key
# This CA is SEPARATE from the server TLS CA (ca.crt).

CERT_DIR="$(dirname "$0")/../compose/mosquitto/certs"
mkdir -p "$CERT_DIR"

CA_KEY="$CERT_DIR/device-ca.key"
CA_CERT="$CERT_DIR/device-ca.crt"
CA_DAYS="${DEVICE_CA_DAYS:-3650}"
CA_SUBJECT="${DEVICE_CA_SUBJECT:-/C=US/ST=CA/O=OpsConductor/OU=IoT/CN=OpsConductor Pulse Device CA}"

if [ -f "$CA_CERT" ] && [ -f "$CA_KEY" ]; then
  echo "Device CA already exists at $CA_CERT -- skipping generation."
  echo "To regenerate, remove $CA_CERT and $CA_KEY first."
  exit 0
fi

echo "==> Generating Device CA private key..."
openssl genrsa -out "$CA_KEY" 4096

echo "==> Generating Device CA certificate (valid $CA_DAYS days)..."
openssl req -new -x509 \
  -key "$CA_KEY" \
  -out "$CA_CERT" \
  -days "$CA_DAYS" \
  -subj "$CA_SUBJECT" \
  -addext "basicConstraints=critical,CA:TRUE,pathlen:0" \
  -addext "keyUsage=critical,keyCertSign,cRLSign"

echo "==> Device CA created:"
echo "    Certificate: $CA_CERT"
echo "    Private key: $CA_KEY"
echo ""
echo "    Fingerprint:"
openssl x509 -in "$CA_CERT" -noout -fingerprint -sha256
echo ""
echo "    Subject:"
openssl x509 -in "$CA_CERT" -noout -subject
echo ""
echo "NOTE: In production, use an external CA and set DEVICE_CA_CERT_PATH / DEVICE_CA_KEY_PATH"
echo "      environment variables instead of using this self-signed CA."

