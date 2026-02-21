# Fix: npm Global Install Permissions + Reinstall mermaid-cli

## Problem
`npm install -g` fails with EACCES because the global npm prefix is `/usr`
(owned by root). This forces fallback to `npx`, which uses cached/old versions
and is not a proper install.

## Fix: Configure user-local npm global directory

Run these commands in order. Each must succeed before the next.

### Step 1: Create user-local npm global directory
```bash
mkdir -p ~/.npm-global
```

### Step 2: Set npm to use it (user-scoped, no sudo needed)
```bash
npm config set prefix ~/.npm-global --location user
```

Verify it took effect:
```bash
npm config get prefix
# Expected output: /home/opsconductor/.npm-global
```

### Step 3: Add to PATH permanently
```bash
echo 'export PATH="$HOME/.npm-global/bin:$PATH"' >> ~/.bashrc
source ~/.bashrc
```

Verify PATH includes the new directory:
```bash
echo $PATH | tr ':' '\n' | grep npm-global
# Expected: /home/opsconductor/.npm-global
```

### Step 4: Install mermaid-cli at latest version — no sudo, no npx fallback
```bash
npm install -g @mermaid-js/mermaid-cli@11.12.0
```

Verify:
```bash
mmdc --version
# Expected: 11.12.0
which mmdc
# Expected: /home/opsconductor/.npm-global/bin/mmdc
```

---

## Re-render the reference architecture diagram with the proper install

Now that mmdc is correctly installed, re-render cleanly:

### Step 5: Re-render PNG (high resolution)
```bash
mmdc \
  -i docs/diagrams/reference-architecture.mmd \
  -o docs/diagrams/reference-architecture.png \
  -c docs/diagrams/mermaid-config.json \
  -w 3200 \
  -H 4800 \
  --backgroundColor "#0d1117"
```

### Step 6: Re-render PDF
```bash
mmdc \
  -i docs/diagrams/reference-architecture.mmd \
  -o docs/diagrams/reference-architecture.pdf \
  -c docs/diagrams/mermaid-config.json \
  -w 3200 \
  -H 4800 \
  --backgroundColor "#0d1117"
```

### Step 7: Verify output sizes (both should be > 100KB)
```bash
ls -lh docs/diagrams/reference-architecture.png
ls -lh docs/diagrams/reference-architecture.pdf
file docs/diagrams/reference-architecture.png
file docs/diagrams/reference-architecture.pdf
```

If either file is under 50KB, the diagram rendered blank or clipped.
Retry with `-w 4000 -H 6000`.

### Step 8: Commit and push
```bash
git add docs/diagrams/reference-architecture.png \
        docs/diagrams/reference-architecture.pdf
git commit -m "docs: re-render architecture diagram at full resolution with mmdc 11.12.0"
git push origin main
git log --oneline -3
```
