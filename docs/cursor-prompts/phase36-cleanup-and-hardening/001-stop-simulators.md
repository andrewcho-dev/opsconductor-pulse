# 001: Stop Device Simulators

## Task

Find and stop all running device simulators that are generating traffic to the ingest endpoint.

## Investigation Steps

### 1. Check Docker Containers

```bash
# List all running containers
docker compose ps

# Look for simulator-related containers
docker ps | grep -i simul

# Check container logs for activity
docker compose logs --tail=50 simulator 2>/dev/null || echo "No simulator container"
```

### 2. Check Background Processes

```bash
# Find Python simulator processes
ps aux | grep -i simul | grep -v grep

# Find any process connecting to ingest port
lsof -i :8080 | grep -i python
lsof -i :443 | grep -i python

# Check for node-based simulators
ps aux | grep -i "node.*device" | grep -v grep
```

### 3. Check Cron Jobs

```bash
# System cron
crontab -l
cat /etc/cron.d/*

# Check for systemd timers
systemctl list-timers --all | grep -i simul
```

### 4. Check Supervisor/PM2

```bash
# Supervisor
supervisorctl status 2>/dev/null || echo "No supervisor"

# PM2
pm2 list 2>/dev/null || echo "No PM2"
```

## Stop Commands

### Docker Containers

```bash
# Stop specific simulator containers
docker compose stop simulator device-sim iot-simulator 2>/dev/null

# Or remove them entirely
docker compose rm -f simulator device-sim iot-simulator 2>/dev/null

# Check docker-compose.yml for simulator services and comment them out
```

### Background Processes

```bash
# Kill Python simulators
pkill -f "python.*simulat"
pkill -f "python.*device.*sim"

# Kill Node simulators
pkill -f "node.*simulat"

# More aggressive - kill anything hitting ingest endpoint
# (be careful with this one)
# fuser -k 8080/tcp
```

### Systemd Services

```bash
# Stop and disable simulator services
sudo systemctl stop device-simulator 2>/dev/null
sudo systemctl disable device-simulator 2>/dev/null
```

## Verify Stopped

```bash
# Watch ingest logs - should see traffic stop
docker compose logs -f ingest_iot 2>&1 | head -100

# Check for new connections
watch -n 1 'netstat -an | grep :8080 | wc -l'

# Monitor database log growth
watch -n 5 'docker compose exec postgres psql -U iot -d iotcloud -t -c "SELECT COUNT(*) FROM activity_log;"'
```

## Prevent Restart

### Comment Out in docker-compose.yml

```yaml
# Comment out or remove simulator services:
#  simulator:
#    build: ./services/simulator
#    ...
```

### Remove from Startup Scripts

Check and update:
- `Makefile` - remove simulator targets from default
- `scripts/start-all.sh` - remove simulator startup
- `.env` - disable simulator flags

### Create Disable Flag

**File:** `services/simulator/DISABLED`

```
# This file prevents the simulator from starting
# Remove this file to re-enable device simulation
# Disabled on: 2024-XX-XX
# Reason: Cleanup for fresh test environment
```

Update simulator entrypoint to check for this file:

```bash
#!/bin/bash
if [ -f /app/DISABLED ]; then
  echo "Simulator disabled - DISABLED file exists"
  exit 0
fi
# ... rest of startup
```

## Verification

```bash
# Confirm no simulator processes
ps aux | grep -c simul  # Should be 0 or just grep itself

# Confirm no new log entries (wait 60 seconds)
BEFORE=$(docker compose exec postgres psql -U iot -d iotcloud -t -c "SELECT COUNT(*) FROM activity_log;")
sleep 60
AFTER=$(docker compose exec postgres psql -U iot -d iotcloud -t -c "SELECT COUNT(*) FROM activity_log;")
echo "Before: $BEFORE, After: $AFTER"
# Should be the same or very close
```
