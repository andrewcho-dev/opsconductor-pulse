# Phase 93 — Verify, Commit, Push

## Step 1: Verify all output files exist

```bash
ls -lh docs/diagrams/
```

Expected files:
- `reference-architecture.md`   — Mermaid source (markdown wrapper)
- `reference-architecture.mmd`  — Raw Mermaid source
- `reference-architecture.png`  — Rendered image
- `reference-architecture.pdf`  — Rendered PDF
- `mermaid-config.json`         — Render config

Both PNG and PDF should be > 50KB. If either is < 10KB it likely rendered blank
(retry with larger -w/-H values from the troubleshooting section in 002-render.md).

## Step 2: Quick visual check

Open the PNG:
```bash
# If xdg-open is available:
xdg-open docs/diagrams/reference-architecture.png

# Or view in VS Code:
code docs/diagrams/reference-architecture.png
```

Confirm:
- Dark background (#0d1117)
- All subgraph boxes visible (External Actors, Ingestion, Data, Evaluation, etc.)
- Connection arrows between components
- Text labels readable

## Step 3: Commit and push

```bash
git add docs/diagrams/
git commit -m "docs: add Mermaid reference architecture diagram (PNG + PDF)"
git push origin main
git log --oneline -3
```

## Step 4: Update ARCHITECTURE.md to reference the diagram

Add this line near the top of `docs/ARCHITECTURE.md`, just after the title/description:

```markdown
> 📊 **Visual diagram**: See [docs/diagrams/reference-architecture.pdf](diagrams/reference-architecture.pdf)
> or view the [Mermaid source](diagrams/reference-architecture.md) which renders in GitHub.
```

Then commit:
```bash
git add docs/ARCHITECTURE.md
git commit -m "docs: link reference architecture diagram from ARCHITECTURE.md"
git push origin main
```
