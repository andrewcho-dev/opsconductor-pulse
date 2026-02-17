import { useMemo, useReducer, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { PageHeader } from "@/components/shared";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import { fetchSites } from "@/services/api/sites";
import { fetchAlertRules } from "@/services/api/alert-rules";
import { provisionDevice } from "@/services/api/devices";
import { apiPost } from "@/services/api/client";

type WizardStep = 1 | 2 | 3 | 4;

type WizardState = {
  deviceId: string;
  displayName: string;
  model: string;
  siteId: string;
  tags: Array<{ key: string; value: string }>;
  notes: string;
  selectedRuleIds: string[];
  credentials: {
    device_id: string;
    api_token: string;
    mqtt_topic: string;
  } | null;
};

type Action =
  | { type: "set"; key: keyof WizardState; value: unknown }
  | { type: "setTag"; index: number; key: "key" | "value"; value: string }
  | { type: "addTag" }
  | { type: "removeTag"; index: number };

const DEVICE_ID_PATTERN = /^[a-z0-9][a-z0-9-_]*$/;

function reducer(state: WizardState, action: Action): WizardState {
  switch (action.type) {
    case "set":
      return { ...state, [action.key]: action.value };
    case "setTag":
      return {
        ...state,
        tags: state.tags.map((tag, i) =>
          i === action.index ? { ...tag, [action.key]: action.value } : tag
        ),
      };
    case "addTag":
      return { ...state, tags: [...state.tags, { key: "", value: "" }] };
    case "removeTag":
      return {
        ...state,
        tags: state.tags.filter((_, i) => i !== action.index),
      };
    default:
      return state;
  }
}

const initialState: WizardState = {
  deviceId: "",
  displayName: "",
  model: "",
  siteId: "",
  tags: [{ key: "", value: "" }],
  notes: "",
  selectedRuleIds: [],
  credentials: null,
};

export default function SetupWizard() {
  const [step, setStep] = useState<WizardStep>(1);
  const [submitting, setSubmitting] = useState(false);
  const [confirmAbandon, setConfirmAbandon] = useState(false);
  const [state, dispatch] = useReducer(reducer, initialState);

  const { data: sitesData } = useQuery({
    queryKey: ["wizard-sites"],
    queryFn: fetchSites,
  });
  const { data: rulesData } = useQuery({
    queryKey: ["wizard-alert-rules"],
    queryFn: () => fetchAlertRules(200),
  });

  const invalidDeviceId = state.deviceId.length > 0 && !DEVICE_ID_PATTERN.test(state.deviceId);
  const dots = [1, 2, 3, 4];

  const tagList = useMemo(
    () =>
      state.tags
        .map((tag) => [tag.key.trim(), tag.value.trim()].filter(Boolean).join("="))
        .filter(Boolean),
    [state.tags]
  );

  async function finishProvision() {
    setSubmitting(true);
    try {
      const res = await provisionDevice({
        name: state.deviceId,
        device_type: state.model || "generic",
        site_id: state.siteId || undefined,
        tags: tagList,
      });

      for (const ruleId of state.selectedRuleIds) {
        try {
          await apiPost(`/customer/devices/${encodeURIComponent(res.device_id)}/alert-rules`, {
            rule_id: ruleId,
          });
        } catch {
          // Ignore missing assignment endpoint and continue wizard flow.
        }
      }

      dispatch({
        type: "set",
        key: "credentials",
        value: {
          device_id: res.device_id,
          api_token: res.password,
          mqtt_topic: `devices/${res.device_id}/telemetry`,
        },
      });
      setStep(4);
    } finally {
      setSubmitting(false);
    }
  }

  function downloadEnv() {
    if (!state.credentials) return;
    const content = `DEVICE_ID=${state.credentials.device_id}\nAPI_TOKEN=${state.credentials.api_token}\nMQTT_TOPIC=${state.credentials.mqtt_topic}\n`;
    const blob = new Blob([content], { type: "text/plain;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `device-${state.credentials.device_id}.env`;
    a.click();
    URL.revokeObjectURL(url);
  }

  return (
    <div className="space-y-6">
      <PageHeader title="Guided Setup Wizard" description="Identity -> Tags -> Rules -> Credentials" />
      <div className="flex items-center gap-2">
        {dots.map((dot) => (
          <span
            key={dot}
            className={`inline-block h-2.5 w-2.5 rounded-full ${
              dot <= step ? "bg-primary" : "bg-muted"
            }`}
          />
        ))}
      </div>

      <div className="space-y-4 rounded-md border border-border p-4">
        {step === 1 && (
          <div className="space-y-3">
            <h3 className="font-medium">Step 1 - Device Identity</h3>
            <div>
              <label className="text-sm text-muted-foreground">Device ID</label>
              <Input
                value={state.deviceId}
                onChange={(e) => dispatch({ type: "set", key: "deviceId", value: e.target.value })}
              />
              {invalidDeviceId && (
                <p className="text-sm text-red-600">
                  Device ID must match /^[a-z0-9][a-z0-9-_]*$/
                </p>
              )}
            </div>
            <div>
              <label className="text-sm text-muted-foreground">Display Name</label>
              <Input
                value={state.displayName}
                onChange={(e) => dispatch({ type: "set", key: "displayName", value: e.target.value })}
              />
            </div>
            <div>
              <label className="text-sm text-muted-foreground">Model / Device Type</label>
              <Input
                value={state.model}
                onChange={(e) => dispatch({ type: "set", key: "model", value: e.target.value })}
              />
            </div>
            <div>
              <label className="text-sm text-muted-foreground">Site</label>
              <select
                className="h-9 w-full rounded-md border border-input bg-background px-2 text-sm"
                value={state.siteId}
                onChange={(e) => dispatch({ type: "set", key: "siteId", value: e.target.value })}
              >
                <option value="">Select site</option>
                {(sitesData?.sites ?? []).map((site) => (
                  <option key={site.site_id} value={site.site_id}>
                    {site.name}
                  </option>
                ))}
              </select>
            </div>
          </div>
        )}

        {step === 2 && (
          <div className="space-y-3">
            <h3 className="font-medium">Step 2 - Tags & Metadata</h3>
            {state.tags.map((tag, idx) => (
              <div key={idx} className="grid grid-cols-[1fr_1fr_auto] gap-2">
                <Input
                  placeholder="key"
                  value={tag.key}
                  onChange={(e) => dispatch({ type: "setTag", index: idx, key: "key", value: e.target.value })}
                />
                <Input
                  placeholder="value"
                  value={tag.value}
                  onChange={(e) =>
                    dispatch({ type: "setTag", index: idx, key: "value", value: e.target.value })
                  }
                />
                <Button variant="outline" onClick={() => dispatch({ type: "removeTag", index: idx })}>
                  x
                </Button>
              </div>
            ))}
            <Button variant="outline" onClick={() => dispatch({ type: "addTag" })}>
              Add Tag
            </Button>
            <div>
              <label className="text-sm text-muted-foreground">Notes</label>
              <Textarea
                value={state.notes}
                onChange={(e) => dispatch({ type: "set", key: "notes", value: e.target.value })}
              />
            </div>
          </div>
        )}

        {step === 3 && (
          <div className="space-y-3">
            <h3 className="font-medium">Step 3 - Alert Rules</h3>
            <div className="space-y-2">
              {(rulesData?.rules ?? []).map((rule) => {
                const selected = state.selectedRuleIds.includes(String(rule.rule_id));
                return (
                  <label
                    key={String(rule.rule_id)}
                    className="flex items-center justify-between rounded border border-border p-2 text-sm"
                  >
                    <div>
                      <div className="font-medium">{rule.name}</div>
                      <div className="text-sm text-muted-foreground">
                        {rule.metric_name} {rule.operator} {rule.threshold}
                      </div>
                    </div>
                    <input
                      type="checkbox"
                      checked={selected}
                      onChange={(e) => {
                        if (e.target.checked) {
                          dispatch({
                            type: "set",
                            key: "selectedRuleIds",
                            value: [...state.selectedRuleIds, String(rule.rule_id)],
                          });
                        } else {
                          dispatch({
                            type: "set",
                            key: "selectedRuleIds",
                            value: state.selectedRuleIds.filter((id) => id !== String(rule.rule_id)),
                          });
                        }
                      }}
                    />
                  </label>
                );
              })}
            </div>
          </div>
        )}

        {step === 4 && state.credentials && (
          <div className="space-y-3">
            <h3 className="font-medium">Step 4 - Credentials</h3>
            <div className="rounded border border-yellow-500/40 bg-yellow-500/10 p-3 text-sm text-yellow-700 dark:text-yellow-300">
              These credentials are shown once. Store them securely.
            </div>
            <div className="grid gap-2 text-sm">
              <div>
                <div className="text-sm text-muted-foreground">Device ID</div>
                <div className="font-mono">{state.credentials.device_id}</div>
              </div>
              <div>
                <div className="text-sm text-muted-foreground">API Token</div>
                <div className="font-mono">{state.credentials.api_token}</div>
              </div>
              <div>
                <div className="text-sm text-muted-foreground">MQTT Topic</div>
                <div className="font-mono">{state.credentials.mqtt_topic}</div>
              </div>
            </div>
            <Button onClick={downloadEnv}>Download device-{state.credentials.device_id}.env</Button>
          </div>
        )}
      </div>

      <div className="flex gap-2">
        {step > 1 && step < 4 && (
          <Button variant="outline" onClick={() => setStep((step - 1) as WizardStep)} disabled={submitting}>
            Back
          </Button>
        )}
        {step < 3 && (
          <Button
            onClick={() => setStep((step + 1) as WizardStep)}
            disabled={submitting || (step === 1 && (!!invalidDeviceId || !state.deviceId.trim()))}
          >
            Next
          </Button>
        )}
        {step === 3 && (
          <>
            <Button variant="outline" onClick={() => setStep(4)} disabled={submitting}>
              Skip
            </Button>
            <Button onClick={finishProvision} disabled={submitting}>
              {submitting ? "Provisioning..." : "Finish"}
            </Button>
          </>
        )}
        {step < 4 && (
          <Button
            variant="ghost"
            onClick={() => {
              if (step > 1) {
                setConfirmAbandon(true);
                return;
              }
              setStep(1);
            }}
          >
            Cancel
          </Button>
        )}
      </div>

      <AlertDialog open={confirmAbandon} onOpenChange={setConfirmAbandon}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Abandon Setup</AlertDialogTitle>
            <AlertDialogDescription>
              Abandon setup? Your device won't be provisioned.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction
              onClick={() => {
                setStep(1);
                setConfirmAbandon(false);
              }}
            >
              Abandon
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}
