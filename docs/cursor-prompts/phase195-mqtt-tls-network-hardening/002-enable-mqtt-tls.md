# Task 2: Enable MQTT TLS in docker-compose and EMQX Configuration

## Context

EMQX is currently configured with TLS disabled. All device MQTT traffic goes in cleartext. TLS must be enabled for port 8883 (standard MQTT-TLS) while keeping port 1883 available for internal service-to-service traffic on the Docker network only (not exposed externally).

## Actions

1. Read `compose/docker-compose.yml` in full, focusing on the EMQX service block.

2. In the EMQX service, change:
   ```yaml
   MQTT_TLS: "false"
   ```
   to:
   ```yaml
   MQTT_TLS: "true"
   ```

3. Remove or set to `"false"` any `MQTT_TLS_INSECURE` environment variable.

4. Add TLS certificate paths to the EMQX service environment:
   ```yaml
   EMQX_LISTENERS__SSL__DEFAULT__SSL_OPTIONS__CACERTFILE: "/etc/emqx/certs/ca.crt"
   EMQX_LISTENERS__SSL__DEFAULT__SSL_OPTIONS__CERTFILE: "/etc/emqx/certs/server.crt"
   EMQX_LISTENERS__SSL__DEFAULT__SSL_OPTIONS__KEYFILE: "/etc/emqx/certs/server.key"
   EMQX_LISTENERS__SSL__DEFAULT__BIND: "0.0.0.0:8883"
   ```

5. Add a volume mount for the cert directory in the EMQX service:
   ```yaml
   volumes:
     - ./certs/emqx:/etc/emqx/certs:ro
   ```

6. Expose port 8883 in the EMQX service ports section (for external device connections). Keep 1883 bound only to `127.0.0.1` or the internal Docker network (not `0.0.0.0`) so it is not reachable from outside.

7. In all other services that set `MQTT_TLS: "false"` or `MQTT_TLS_INSECURE: "true"`, remove those lines or set them to the correct values:
   - Internal services connecting on port 1883 (same Docker network): `MQTT_TLS: "false"` is acceptable for internal only.
   - Any service connecting on 8883: must have TLS enabled.

8. Do not change EMQX authentication configuration.

## Verification

```bash
grep 'MQTT_TLS_INSECURE.*true' compose/docker-compose.yml
# Must return zero results

grep '8883' compose/docker-compose.yml
# Must show port 8883 exposed for EMQX
```
