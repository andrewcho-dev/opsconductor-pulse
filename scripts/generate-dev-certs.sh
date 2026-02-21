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
