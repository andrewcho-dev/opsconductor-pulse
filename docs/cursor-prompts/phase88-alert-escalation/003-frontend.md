# Phase 88 — Frontend: Escalation Policy UI

## New files
- `frontend/src/features/escalation/EscalationPoliciesPage.tsx`
- `frontend/src/features/escalation/EscalationPolicyModal.tsx`
- `frontend/src/services/api/escalation.ts`

## API service: escalation.ts

```typescript
export interface EscalationLevel {
  level_id?: number;
  level_number: number;
  delay_minutes: number;
  notify_email?: string;
  notify_webhook?: string;
}

export interface EscalationPolicy {
  policy_id: number;
  tenant_id: string;
  name: string;
  description?: string;
  is_default: boolean;
  levels: EscalationLevel[];
  created_at: string;
  updated_at: string;
}

export async function listEscalationPolicies(): Promise<{ policies: EscalationPolicy[] }>
export async function createEscalationPolicy(body: Omit<EscalationPolicy, 'policy_id' | 'tenant_id' | 'created_at' | 'updated_at'>): Promise<EscalationPolicy>
export async function updateEscalationPolicy(id: number, body: Partial<EscalationPolicy>): Promise<EscalationPolicy>
export async function deleteEscalationPolicy(id: number): Promise<void>
```

All functions call `apiGet`/`apiPost`/`apiPut`/`apiDelete` from `@/services/api/client`.

## EscalationPoliciesPage layout

```
PageHeader: "Escalation Policies"  [New Policy button]

Table:
Name | Default | # Levels | Created | Actions
-----|---------|---------|---------|--------
...  | ✓ badge | 3       | 2d ago  | Edit  Delete
```

- "New Policy" and row Edit open `EscalationPolicyModal` (create or edit mode)
- Delete shows a confirm dialog before calling deleteEscalationPolicy
- Use react-query: `useQuery(['escalation-policies'], listEscalationPolicies)`
- Invalidate on mutation success

## EscalationPolicyModal

shadcn Dialog with form:

**Top section:**
- Name (text input, required)
- Description (textarea, optional)
- Is Default (checkbox) — label: "Make this the default policy for new alert rules"

**Levels section:**
- Header: "Escalation Levels" + [Add Level] button
- Dynamic list of level rows. Each row:
  - Level # (read-only, auto 1-based)
  - Delay: `[___] minutes` (number input, min 1)
  - Email: text input, placeholder "notify@example.com" (optional)
  - Webhook: text input, placeholder "https://..." (optional)
  - [×] remove button (disabled if only 1 level)
- Max 5 levels enforced (hide Add Level button when 5 reached)

**Footer:** Cancel | Save

## Route + Sidebar

- Add route in `frontend/src/app/router.tsx`:
  ```tsx
  { path: '/escalation-policies', element: <EscalationPoliciesPage /> }
  ```
- Add "Escalation" link under the Monitoring group in `AppSidebar.tsx`
