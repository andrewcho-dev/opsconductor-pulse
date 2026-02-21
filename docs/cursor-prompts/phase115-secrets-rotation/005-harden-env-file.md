# 005 — Harden .env File Permissions

## Goal

The `.env` file now contains production secrets worth protecting. Lock
down its filesystem permissions so only the deployment user can read it.

## Apply Permissions

```bash
cd ~/simcloud/compose

# Only the owner can read/write. No group, no other.
chmod 600 .env

# Verify
ls -la .env
# Expected: -rw------- 1 opsconductor opsconductor ... .env
```

## Also Protect the Backup

```bash
chmod 600 .env.bak.*
```

## Verify .gitignore Coverage

Confirm `.env` is excluded from git:

```bash
cd ~/simcloud
git check-ignore compose/.env
# Expected: compose/.env
```

If this returns nothing, add to `.gitignore`:
```
compose/.env
```

## Additional Hardening

### Delete the .env backup after verifying everything works

Once step 006 confirms the full stack is healthy with new credentials:

```bash
cd ~/simcloud/compose
# ONLY after full verification:
rm .env.bak.*
```

The old backup contains dev passwords, but more importantly it proves
the pattern of storing secrets in plaintext files. Remove it.

### Consider shell history

If you typed passwords directly in commands during step 002 (the ALTER
USER commands), clear those from shell history:

```bash
history -d <line_number>
# Or clear all history for this session:
history -c
```

## Notes

- `chmod 600` means only the file owner can read/write. Docker Compose
  runs as this user, so it can still read the file.
- If Docker Compose runs as a different user (e.g., via sudo), ensure
  that user has read access. Use `chown` if needed.
