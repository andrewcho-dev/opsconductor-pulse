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
  echo "Device CA already exists at $CA_CERT -- skipping key/cert generation."
  echo "To regenerate, remove $CA_CERT and $CA_KEY first."
else
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
fi

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

# Create combined CA bundle for Mosquitto (server CA + device CA)
COMBINED="$CERT_DIR/combined-ca.crt"
if [ -f "$CERT_DIR/ca.crt" ]; then
  cat "$CERT_DIR/ca.crt" "$CA_CERT" > "$COMBINED"
else
  # Fallback: at least include the device CA (useful for client auth validation)
  cat "$CA_CERT" > "$COMBINED"
fi
echo "    Combined CA bundle: $COMBINED"

# Generate initial (empty) CRL for Mosquitto.
# Mosquitto fails to start if crlfile is configured but missing.
CRL_FILE="$CERT_DIR/device-crl.pem"
if [ ! -f "$CRL_FILE" ]; then
  echo "==> Generating initial empty Device CRL..."

  # Minimal OpenSSL CA state for CRL generation (no issued certs).
  CA_DB_DIR="$CERT_DIR/device-ca-db"
  mkdir -p "$CA_DB_DIR"
  touch "$CA_DB_DIR/index.txt"
  [ -f "$CA_DB_DIR/serial" ] || echo "01" > "$CA_DB_DIR/serial"
  [ -f "$CA_DB_DIR/crlnumber" ] || echo "01" > "$CA_DB_DIR/crlnumber"

  OPENSSL_CNF="$CA_DB_DIR/openssl.cnf"
  cat > "$OPENSSL_CNF" <<EOF
[ ca ]
default_ca = CA_default

[ CA_default ]
dir               = $CA_DB_DIR
database          = \$dir/index.txt
new_certs_dir     = \$dir/newcerts
serial            = \$dir/serial
crlnumber         = \$dir/crlnumber
default_md        = sha256
default_crl_days  = 30
policy            = policy_any
x509_extensions   = usr_cert

[ policy_any ]
commonName        = supplied

[ usr_cert ]
basicConstraints  = CA:FALSE
EOF

  mkdir -p "$CA_DB_DIR/newcerts"

  openssl ca -gencrl \
    -keyfile "$CA_KEY" \
    -cert "$CA_CERT" \
    -out "$CRL_FILE" \
    -config "$OPENSSL_CNF" 2>/dev/null || true

  # If the openssl ca approach fails, try a simple method using Python + cryptography
  if [ ! -f "$CRL_FILE" ]; then
    python3 -c "
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.backends import default_backend
from datetime import datetime, timezone, timedelta

ca_key = serialization.load_pem_private_key(open('$CA_KEY','rb').read(), None, default_backend())
ca_cert = x509.load_pem_x509_certificate(open('$CA_CERT','rb').read(), default_backend())
now = datetime.now(timezone.utc)
builder = x509.CertificateRevocationListBuilder()
builder = builder.issuer_name(ca_cert.subject)
builder = builder.last_update(now)
builder = builder.next_update(now + timedelta(days=30))
crl = builder.sign(ca_key, hashes.SHA256(), default_backend())
open('$CRL_FILE','wb').write(crl.public_bytes(serialization.Encoding.PEM))
print('Initial empty CRL created')
" || true
  fi

  if [ -f "$CRL_FILE" ]; then
    echo "    Initial CRL: $CRL_FILE"
  else
    echo "WARNING: Failed to create initial CRL at $CRL_FILE"
    echo "         Mosquitto will not start if crlfile is configured without a valid CRL."
  fi
fi

echo "NOTE: In production, use an external CA and set DEVICE_CA_CERT_PATH / DEVICE_CA_KEY_PATH"
echo "      environment variables instead of using this self-signed CA."

