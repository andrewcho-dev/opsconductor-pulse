# Phase 94a — Fix: Install ripgrep + Fix PATH for mmdc + Silence puppeteer warnings

## Problems to fix

1. `rg` (ripgrep) is not installed — causes "rg is not installed" errors in any tool that depends on it
2. `mmdc` is not in `$PATH` in new shell sessions — `~/.npm-global/bin` is set in `~/.bashrc` but not loaded
3. puppeteer deprecation warnings printed to stderr whenever `mmdc` runs — cosmetic but alarming

---

## Fix 1: Install ripgrep

```bash
sudo apt-get update -y && sudo apt-get install -y ripgrep
```

Verify:
```bash
rg --version
# Expected: ripgrep 13.x.x (or similar)
which rg
# Expected: /usr/bin/rg
```

---

## Fix 2: Verify mmdc PATH in current shell

The `~/.npm-global/bin` path was added to `~/.bashrc` in phase 93b, but only takes effect
in new login shells. Confirm it is active NOW:

```bash
echo $PATH | tr ':' '\n' | grep npm-global
# Expected: /home/opsconductor/.npm-global/bin
```

If the line is missing (blank output), source it manually first:
```bash
source ~/.bashrc
echo $PATH | tr ':' '\n' | grep npm-global
```

Then confirm mmdc is found without full path:
```bash
mmdc --version
# Expected: 11.12.0
which mmdc
# Expected: /home/opsconductor/.npm-global/bin/mmdc
```

Also add to `~/.profile` as a belt-and-suspenders fix so it loads in all session types:
```bash
grep -q 'npm-global' ~/.profile || echo 'export PATH="$HOME/.npm-global/bin:$PATH"' >> ~/.profile
source ~/.profile
```

Verify one more time:
```bash
mmdc --version
```

---

## Fix 3: Suppress puppeteer deprecation warnings

puppeteer 23.11.1 is bundled inside `@mermaid-js/mermaid-cli`. Its internal use of
`page.waitForTimeout()` triggers a Node.js deprecation warning to stderr. This is a
known upstream issue in mermaid-cli — it does NOT affect rendering quality or output.

The warning looks like:
```
(node:XXXXX) [DEP0xxx] DeprecationWarning: ...puppeteer...
```

Suppress it for all mmdc invocations by wrapping mmdc in a shell function that sets
the `NODE_NO_WARNINGS` environment variable:

```bash
# Add to ~/.bashrc (after the PATH export)
cat >> ~/.bashrc << 'EOF'

# Suppress puppeteer deprecation noise from mmdc
mmdc() {
  NODE_NO_WARNINGS=1 ~/.npm-global/bin/mmdc "$@"
}
export -f mmdc
EOF

source ~/.bashrc
```

Verify the function is loaded:
```bash
type mmdc
# Expected: mmdc is a function
```

Test that mmdc still works and warnings are gone:
```bash
mmdc --version
# Expected: 11.12.0  (no deprecation warnings)
```

---

## Final verification — all three fixes together

```bash
rg --version
mmdc --version
which mmdc
echo "All environment fixes verified."
```

Expected output (no errors, no warnings):
```
ripgrep X.X.X
11.12.0
mmdc is a function  (or /home/opsconductor/.npm-global/bin/mmdc)
All environment fixes verified.
```

---

## Commit

No code files changed — this is a host environment fix only. No commit needed.
Document it was done:

```bash
git log --oneline -3
```
