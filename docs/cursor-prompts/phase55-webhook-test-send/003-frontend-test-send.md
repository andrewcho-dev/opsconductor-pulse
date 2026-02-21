# Prompt 003 — Frontend: Send Test Button

Read `frontend/src/features/integrations/` — find the integration detail/edit component.
Read existing API client patterns.

## Add API Function

In `frontend/src/services/api/integrations.ts` (or existing file):

```typescript
export interface TestSendResult {
  success: boolean;
  http_status: number | null;
  latency_ms: number;
  error?: string;
}

export async function testSendIntegration(integrationId: string): Promise<TestSendResult> {
  return apiFetch(`/customer/integrations/${integrationId}/test-send`, { method: 'POST' });
}
```

## Add "Send Test" Button

On the webhook integration detail/edit page:
- Add a "Send Test" button (only visible for type='webhook' integrations)
- On click: calls `testSendIntegration(integrationId)`
- While loading: button shows spinner, disabled
- On success: show inline result:
  - Green: "✓ Test sent — HTTP {status} in {latency}ms"
  - Red: "✗ Failed — {error or HTTP status}"
- Clear result after 10 seconds

## Acceptance Criteria

- [ ] "Send Test" button visible on webhook integration detail
- [ ] Button disabled while request in flight
- [ ] Shows success with HTTP status + latency
- [ ] Shows failure with error message
- [ ] Result clears after 10s
- [ ] `npm run build` passes
