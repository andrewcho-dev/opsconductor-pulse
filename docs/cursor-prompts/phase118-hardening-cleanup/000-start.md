# Phase 118 — Hardening, Cleanup, and CI Stabilization

You are executing Phase 118. This phase cleans up accumulated tech debt: uncommitted files, a half-finished logging migration, dead code, broken CI, stale docs, and missing bootstrap logic.

**Read and execute the following prompt files in this exact order.** Each file contains precise instructions — file paths, line numbers, before/after content, shell commands, and verification steps. Follow them exactly.

## Execution Order

Execute these sequentially. Do NOT skip ahead. After each step, run its verification checks before proceeding to the next.

1. **`001-commit-hardening-files.md`** — Stage and commit 6 uncommitted hardening files. This unblocks everything else.
2. **`002-complete-logging-migration.md`** — Move `trace_id_var` into `shared/logging.py`, update 8 import sites, delete `shared/log.py`. Commit.
3. **`003-delete-dead-integrations.md`** — Delete `frontend/src/features/integrations/` (6 orphaned files), remove the README table row, rebuild frontend. Commit.
4. **`004-repo-cleanup-gitignore.md`** — `git rm` debug scripts, delete backup files, delete leftover test file, update `.gitignore`. Commit.
5. **`005-fix-pytest-config.md`** — Remove hardcoded absolute path from `pytest.ini`. Commit.
6. **`006-fix-ci-pipelines.md`** — Remove `|| true` from ESLint and migrations, delete stale artifact upload, fix E2E compose startup/cleanup/healthcheck, add env vars to smoke workflow. Commit.
7. **`007-update-readme.md`** — Fix MQTT port (1883→8883), remove hardcoded IP, update migration instructions and count. Commit.
8. **`008-keycloak-bootstrap-script.md`** — Add `bootstrap_keycloak_profile()` function to `scripts/seed_demo_data.py` with httpx, call it from `main()`. Commit.

## Rules

- Each step produces exactly one git commit. Do not squash or skip commits.
- If a verification check fails, fix the issue before moving on.
- Do not modify files beyond what each prompt specifies.
- Do not add comments, docstrings, or type annotations beyond what is specified.

## Final Verification

After all 8 steps are complete, run every one of these checks:

```bash
git status
# Expected: clean working tree (no unstaged changes)

git log --oneline -8
# Expected: 8 new commits matching the messages from each step

docker compose -f compose/docker-compose.yml config --quiet
# Expected: no errors

cd frontend && npm run build && cd ..
# Expected: builds clean, no references to deleted integrations

grep -r "opsconductor" pytest.ini
# Expected: no output (hardcoded path removed)

grep "|| true" .github/workflows/test.yml
# Expected: only the mypy line (~line 292)

ls frontend/src/features/integrations/ 2>&1
# Expected: "No such file or directory"

git ls-files debug_login*
# Expected: no output (debug scripts untracked)

ls compose/docker-compose.yml.* 2>&1
# Expected: "No such file or directory"

grep -r "from shared.log " services/
# Expected: no output (all imports migrated to shared.logging)

python -c "import ast; ast.parse(open('scripts/seed_demo_data.py').read()); print('OK')"
# Expected: OK

grep "bootstrap_keycloak_profile" scripts/seed_demo_data.py
# Expected: function definition + call in main()
```

If all checks pass, Phase 118 is complete.
