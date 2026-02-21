# 007 — Update README

## Context

`README.md` has stale references: wrong MQTT port, hardcoded dev IP, outdated migration instructions, incorrect migration count.

---

## 7a — Fix MQTT port

**File**: `README.md`, line 17

### Before:
```
# MQTT Broker:       localhost:1883
```

### After:
```
# MQTT Broker:       localhost:8883  (TLS)
```

Port 1883 is internal Docker-network only. External access is on 8883 (TLS).

---

## 7b — Remove hardcoded IP

**File**: `README.md`, lines 14-15

### Before:
```
# Application:       https://192.168.10.53  (or https://localhost)
# Keycloak Admin:    https://192.168.10.53/admin  (admin / admin_dev)
```

### After:
```
# Application:       https://localhost
# Keycloak Admin:    https://localhost/admin  (admin / admin_dev)
```

---

## 7c — Update migration instructions

**File**: `README.md`, lines 224-232

### Before:
```markdown
## Applying Migrations

```bash
# Apply a specific migration
psql "$DATABASE_URL" -f db/migrations/066_escalation_policies.sql

# Apply all pending (in order)
for f in db/migrations/*.sql; do psql "$DATABASE_URL" -f "$f"; done
```
```

### After:
```markdown
## Applying Migrations

```bash
# Apply all pending migrations (idempotent, versioned runner)
python db/migrate.py

# Or apply a specific migration manually
psql "$DATABASE_URL" -f db/migrations/080_iam_permissions.sql
```
```

---

## 7d — Update migration count

**File**: `README.md`, line 121

### Before:
```
  migrations/         # 069 PostgreSQL + TimescaleDB migrations
```

### After:
```
  migrations/         # 080 PostgreSQL + TimescaleDB migrations
```

(There are currently 66 migration files; the highest numbered is 080.)

---

## Commit

```bash
git add README.md
git commit -m "docs: fix MQTT port, remove hardcoded IP, update migration instructions"
```

## Verification

```bash
grep "1883" README.md
# Should return nothing

grep "192.168.10.53" README.md
# Should return nothing

grep "migrate.py" README.md
# Should show the new migration runner reference
```
