# Task 3: Update Python Service MQTT Clients for TLS

## Context

Python services that connect to EMQX on port 8883 must be updated to use TLS. Services that connect internally on port 1883 (same Docker network) may continue without TLS.

## Actions

1. Search for MQTT client connection code across all services:
   ```
   grep -rn 'mqtt\|emqx\|1883\|8883' services/ --include="*.py"
   ```

2. Read each file that contains MQTT connection code.

3. For any service connecting externally (port 8883), add TLS configuration. The pattern for the `paho-mqtt` client (or whichever library is used) is:
   ```python
   import ssl
   tls_context = ssl.create_default_context(cafile="/etc/emqx/certs/ca.crt")
   client.tls_set_context(tls_context)
   ```

4. Ensure the CA cert path is configurable via environment variable:
   ```python
   MQTT_CA_CERT = os.getenv("MQTT_CA_CERT_PATH", "/etc/emqx/certs/ca.crt")
   ```

5. For services that explicitly set `tls_insecure=True` or equivalent: remove that setting.

6. Add the cert volume mount to each affected service in `compose/docker-compose.yml`:
   ```yaml
   volumes:
     - ./certs/emqx:/etc/emqx/certs:ro
   ```

7. Do not change any MQTT topic or authentication logic.

## Verification

```bash
grep -rn 'tls_insecure.*True\|verify.*False' services/
# Must return zero results for MQTT TLS bypass
```
