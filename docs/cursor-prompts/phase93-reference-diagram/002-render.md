# Phase 93 — Render Mermaid to PNG and PDF

## Goal
Use `@mermaid-js/mermaid-cli` (mmdc) to render the Mermaid source to PNG and PDF.

## Step 1: Extract the raw Mermaid source

Create a standalone `.mmd` file from the diagram:

```bash
# Extract just the mermaid block (between the ```mermaid fences)
sed -n '/^```mermaid/,/^```/{/^```/d;p}' \
  docs/diagrams/reference-architecture.md \
  > docs/diagrams/reference-architecture.mmd

# Verify it starts with "flowchart TD"
head -3 docs/diagrams/reference-architecture.mmd
```

## Step 2: Install mermaid-cli (if not already installed)

```bash
# Install globally
npm install -g @mermaid-js/mermaid-cli

# Verify
mmdc --version
```

If npm global install fails due to permissions:
```bash
npx @mermaid-js/mermaid-cli --version
```
(use `npx mmdc` instead of `mmdc` throughout if needed)

## Step 3: Create a Mermaid config file for dark theme + large canvas

Create `docs/diagrams/mermaid-config.json`:
```json
{
  "theme": "dark",
  "flowchart": {
    "htmlLabels": true,
    "curve": "basis",
    "nodeSpacing": 50,
    "rankSpacing": 80
  },
  "themeVariables": {
    "fontSize": "14px",
    "primaryColor": "#1a1a2e",
    "primaryTextColor": "#eee",
    "primaryBorderColor": "#e94560",
    "lineColor": "#888",
    "background": "#0d1117",
    "mainBkg": "#1a1a2e",
    "nodeBorder": "#e94560",
    "clusterBkg": "#16213e",
    "titleColor": "#eee",
    "edgeLabelBackground": "#1a1a2e"
  }
}
```

## Step 4: Render to PNG

```bash
mmdc \
  -i docs/diagrams/reference-architecture.mmd \
  -o docs/diagrams/reference-architecture.png \
  -c docs/diagrams/mermaid-config.json \
  -w 2400 \
  -H 3200 \
  --backgroundColor "#0d1117"
```

Verify:
```bash
ls -lh docs/diagrams/reference-architecture.png
file docs/diagrams/reference-architecture.png
```

## Step 5: Render to PDF

```bash
mmdc \
  -i docs/diagrams/reference-architecture.mmd \
  -o docs/diagrams/reference-architecture.pdf \
  -c docs/diagrams/mermaid-config.json \
  -w 2400 \
  -H 3200 \
  --backgroundColor "#0d1117"
```

Verify:
```bash
ls -lh docs/diagrams/reference-architecture.pdf
file docs/diagrams/reference-architecture.pdf
```

## Troubleshooting

### If mmdc fails with Puppeteer/Chromium error
```bash
# Install Chromium dependency
apt-get install -y chromium-browser 2>/dev/null || \
npx puppeteer browsers install chrome
```

### If output is blank or cut off
Increase `-w` (width) and `-H` (height):
```bash
mmdc -i docs/diagrams/reference-architecture.mmd \
     -o docs/diagrams/reference-architecture.png \
     -c docs/diagrams/mermaid-config.json \
     -w 3200 -H 4800 \
     --backgroundColor "#0d1117"
```

### If theme doesn't apply
Try without the config file first:
```bash
mmdc -i docs/diagrams/reference-architecture.mmd \
     -o docs/diagrams/reference-architecture.png \
     -t dark -w 2400 -H 3200 \
     --backgroundColor "#0d1117"
```
