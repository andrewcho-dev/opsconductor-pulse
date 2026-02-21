# Prompt 005 — Frontend: Credential Download Modal

## Create `frontend/src/features/devices/CredentialModal.tsx`

This modal is shown once after device provisioning and displays MQTT credentials.

Props:
```typescript
interface CredentialModalProps {
  credentials: {
    device_id: string;
    client_id: string;
    password: string;
    broker_url: string;
  };
  deviceName: string;
  onClose: () => void;
}
```

Display:
- Warning banner: "These credentials will not be shown again. Save them now."
- Fields shown as read-only copyable text: Client ID, Password, Broker URL
- "Copy" button next to each field
- "Download .env" button — generates and downloads a file:

```
# OpsConductor/Pulse Device Credentials
# Device: {deviceName}
# Generated: {ISO timestamp}

MQTT_CLIENT_ID={client_id}
MQTT_PASSWORD={password}
MQTT_BROKER_URL={broker_url}
```

- "Close" button — closes modal (warns if credentials not downloaded)

## Wire into AddDeviceModal

After successful provisioning, pass the response to CredentialModal and show it.

## Acceptance Criteria

- [ ] CredentialModal.tsx displays client_id, password, broker_url
- [ ] Warning banner present
- [ ] "Copy" button works for each field
- [ ] "Download .env" generates correct file content
- [ ] Modal shown after successful provisioning
- [ ] `npm run build` passes
