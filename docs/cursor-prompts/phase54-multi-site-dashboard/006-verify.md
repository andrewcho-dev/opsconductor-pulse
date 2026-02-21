# Prompt 006 — Verify Phase 54

## Step 1: Unit Tests

```bash
pytest -m unit -v 2>&1 | tail -40
```

## Step 2: TypeScript Build

```bash
cd frontend && npm run build 2>&1 | tail -10
```

## Step 3: Checklist

### Backend
- [ ] GET /customer/sites returns sites with rollup counts
- [ ] GET /customer/sites/{site_id}/summary returns devices + alerts
- [ ] 404 on unknown site_id

### Frontend
- [ ] SitesPage.tsx exists
- [ ] SiteDetailPage.tsx exists
- [ ] `/sites` and `/sites/:siteId` routes registered
- [ ] "Sites" link in navigation
- [ ] `frontend/src/services/api/sites.ts` exists
- [ ] `useSites` hook exists

### Unit Tests
- [ ] test_sites_endpoints.py with 6 tests

## Report

Output PASS / FAIL per criterion.
