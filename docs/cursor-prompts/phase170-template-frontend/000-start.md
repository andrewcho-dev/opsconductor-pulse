# Phase 170 — Template Management Frontend

## Goal

Create the Template List and Template Detail pages in the frontend, with API service functions, routing, and sidebar navigation.

## Prerequisites

- Phase 168 complete (template backend endpoints exist)
- Frontend stack: React 19, TypeScript, shadcn/ui, TanStack Query, Tailwind CSS, React Router v7
- UI patterns: See existing pages like `SitesPage`, `AlertRulesPage` for DataTable patterns

## Execution Order

| Step | File | Description |
|------|------|-------------|
| 1 | `001-api-functions.md` | Template API service functions + TypeScript types |
| 2 | `002-template-list.md` | TemplateListPage component |
| 3 | `003-template-detail.md` | TemplateDetailPage with tabs |
| 4 | `004-routes-sidebar.md` | Wire routes and sidebar nav |
| 5 | `005-update-docs.md` | Update frontend docs |

## Verification

```bash
cd frontend && npx tsc --noEmit && npm run build
```

Manual:
1. Navigate to /app/templates → see list of system templates
2. Click a system template → see tabbed detail view
3. Click "Clone" on a system template → tenant copy created
4. Create a new tenant template → appears in list
5. Edit tenant template metrics/commands/slots → changes persist
