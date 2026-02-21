# 004 — Repo Cleanup + Gitignore

## Context

Several files need cleanup:
- 3 debug scripts tracked in git (should never have been committed)
- 2 backup docker-compose files (untracked, contain potentially pre-rotation secrets)
- 1 leftover test file (already gitignored but still on disk)
- `.gitignore` missing rules for debug scripts and backup files
- Strategy docs in `docs/` should be gitignored

## Step 1 — Remove tracked debug scripts from git

```bash
git rm debug_login.py debug_login_detailed.py decode_jwt.py
```

This removes them from git tracking AND deletes the working tree copies.

## Step 2 — Delete untracked backup files

```bash
rm compose/docker-compose.yml.bak-20260215-090906
rm compose/docker-compose.yml.pre-rotation.20260215-092318
```

## Step 3 — Delete leftover test file

```bash
rm -f tests/e2e/test_phase80_83_sanity.py
```

(Already gitignored at line 49, not tracked — just removing from disk.)

## Step 4 — Update `.gitignore`

Add the following lines to the end of `.gitignore`:

```gitignore

# Debug scripts
debug_*.py
decode_jwt.py

# Backup / rotation snapshots
*.bak-*
*.pre-rotation.*

# Internal strategy docs
docs/Reply_to_*
docs/OpsConductor-Pulse_Software_Strategy*
```

## Step 5 — Commit

```bash
git add .gitignore
git commit -m "chore: remove debug scripts, backup files; update .gitignore"
```

## Verification

```bash
# Debug scripts no longer tracked
git ls-files debug_login*
# Should return nothing

# Backup files gone
ls compose/docker-compose.yml.*
# Should error or return nothing

# Gitignore has new rules
grep "debug_\*.py" .gitignore
grep "bak-" .gitignore
grep "Reply_to_" .gitignore
```
