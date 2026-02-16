#!/usr/bin/env bash
set -euo pipefail

# Test script: generate a device cert and test mTLS MQTT connection
# Prerequisites:
#   - Device CA generated (./scripts/generate_device_ca.sh)
#   - Mosquitto running with mTLS config
#   - Device registered in DB

CERT_DIR="$(dirname "$0")/../compose/mosquitto/certs"
TENANT_ID="${1:-tenant-test}"
DEVICE_ID="${2:-DEVICE-001}"
MQTT_HOST="${3:-localhost}"
MQTT_PORT="${4:-8883}"

WORK_DIR=$(mktemp -d)
trap "rm -rf $WORK_DIR" EXIT

CN="${TENANT_ID}/${DEVICE_ID}"

echo "==> Generating device key and CSR for CN=${CN}..."
openssl genrsa -out "$WORK_DIR/device.key" 2048

openssl req -new \
  -key "$WORK_DIR/device.key" \
  -out "$WORK_DIR/device.csr" \
  -subj "/CN=${CN}/O=OpsConductor Pulse"

echo "==> Signing with Device CA..."
openssl x509 -req \
  -in "$WORK_DIR/device.csr" \
  -CA "$CERT_DIR/device-ca.crt" \
  -CAkey "$CERT_DIR/device-ca.key" \
  -CAcreateserial \
  -out "$WORK_DIR/device.crt" \
  -days 365 \
  -sha256

echo "==> Device certificate:"
openssl x509 -in "$WORK_DIR/device.crt" -noout -subject -issuer -dates

echo ""
echo "==> Testing MQTT publish with mTLS..."
mosquitto_pub \
  --cafile "$CERT_DIR/combined-ca.crt" \
  --cert "$WORK_DIR/device.crt" \
  --key "$WORK_DIR/device.key" \
  -h "$MQTT_HOST" \
  -p "$MQTT_PORT" \
  -t "tenant/${TENANT_ID}/device/${DEVICE_ID}/telemetry" \
  -m "{\"ts\":\"$(date -u +%Y-%m-%dT%H:%M:%SZ)\",\"site_id\":\"site-1\",\"metrics\":{\"temp\":22.5}}" \
  -d

echo ""
echo "==> Publish complete. Check ingest_iot logs for acceptance/rejection."

