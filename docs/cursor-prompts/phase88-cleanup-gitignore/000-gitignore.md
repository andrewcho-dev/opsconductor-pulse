# Cleanup: Add Untracked Sanity Artifacts to .gitignore

## Context

Several ad-hoc sanity/debug files are untracked in the repo root. They should
be ignored going forward but kept on disk.

## Step 1: Append to .gitignore

Open `.gitignore` at the repo root and append the following block at the end:

```
# Ad-hoc sanity/debug artifacts
FINAL_SANITY_REPORT.txt
SANITY_TEST_CHECKLIST.md
SANITY_TEST_REPORT.txt
inspect_ui.py
run_sanity_test.sh
sanity_test_standalone.py
tests/e2e/test_phase80_83_sanity.py
```

## Step 2: Verify

```bash
git status --short
```

The 7 files above should no longer appear as `??`. The AWS PDF is not listed
here — decide manually: commit it to `docs/` or move it outside the repo.

## Step 3: Commit and push

```bash
git add .gitignore
git commit -m "chore: ignore ad-hoc sanity/debug artifacts"
git push origin main
git log --oneline -3
```
