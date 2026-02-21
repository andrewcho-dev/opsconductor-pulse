# Prompt 003 — Verify Phase 80

## Step 1
```bash
cd frontend && npm run build 2>&1 | tail -20
```

## Checklist
- [ ] 5 nav groups in customer sidebar (Overview, Fleet, Monitoring, Data & Integrations, Settings)
- [ ] Each group collapsible with chevron
- [ ] Collapsed state persists via localStorage
- [ ] Integrations merged into Data & Integrations (no separate Integrations section)
- [ ] Open alert count badge on Alerts item
- [ ] Red dot on Monitoring header when collapsed + alerts exist
- [ ] Operator nav also grouped and collapsible
- [ ] npm run build passes

## Step 2: Commit and push
```bash
git add -A
git commit -m "Phase 80: Restructure sidebar with collapsible grouped navigation and alert badge

- 5 customer nav groups: Overview, Fleet, Monitoring, Data & Integrations, Settings
- Each group collapsible with chevron, state persisted in localStorage
- Integrations merged into Data & Integrations group
- Live open alert count badge on Alerts nav item (30s refresh)
- Operator nav also grouped and collapsible"
git push origin main
git log --oneline -3
```
