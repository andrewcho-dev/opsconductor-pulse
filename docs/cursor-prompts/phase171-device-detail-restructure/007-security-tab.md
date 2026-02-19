# Task 7: Security Tab

## Create component in `frontend/src/features/devices/` (e.g., `DeviceSecurityTab.tsx`)

Consolidates DeviceApiTokensPanel + DeviceCertificatesTab.

### Component Structure

```
SecurityTab
├── API Tokens Section
│   ├── Section header: "API Tokens" + "Create Token" button
│   ├── Tokens table (reuse from DeviceApiTokensPanel)
│   │   ├── Columns: Name/Label, Created, Last Used, Status, Actions (Revoke, Rotate)
│   │   └── Expandable row: token preview (masked)
│   ├── Create token dialog
│   └── Revoke confirmation dialog
│
└── Certificates Section
    ├── Section header: "mTLS Certificates"
    ├── Certificates table (reuse from DeviceCertificatesTab)
    │   ├── Columns: Subject CN, Issuer, Valid From, Valid To, Status, Actions
    │   └── Certificate detail expansion
    ├── Upload certificate button
    └── Revoke certificate dialog
```

### Implementation Approach

This tab is primarily a reorganization — the existing `DeviceApiTokensPanel` and `DeviceCertificatesTab` components already implement the full functionality. The approach is:

1. **Read** the existing `DeviceApiTokensPanel.tsx` and `DeviceCertificatesTab.tsx` to understand their props and data requirements.
2. **Move** their content into the Security tab component, either:
   - Import and render them directly (quickest approach)
   - Extract and inline their JSX (if they have unwanted wrappers)

```tsx
// Simplest approach — compose existing components:
function SecurityTab({ deviceId }: { deviceId: string }) {
  return (
    <div className="space-y-8">
      <section>
        <h3 className="text-lg font-semibold mb-4">API Tokens</h3>
        <DeviceApiTokensPanel deviceId={deviceId} />
      </section>
      <section>
        <h3 className="text-lg font-semibold mb-4">mTLS Certificates</h3>
        <DeviceCertificatesTab deviceId={deviceId} />
      </section>
    </div>
  );
}
```

If the existing components have outer Card wrappers or panel headers that would look redundant inside the tab, refactor them to accept a `bare` prop or extract the inner content.

### Data Fetching

The existing components handle their own data fetching. No additional queries needed.

## Verification

1. API tokens section renders with existing token data
2. Create/revoke/rotate token actions work
3. Certificates section renders
4. Upload/revoke certificate actions work
5. No visual regressions from the component migration
