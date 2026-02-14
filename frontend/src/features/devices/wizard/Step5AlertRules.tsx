import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  applyAlertRuleTemplates,
  createAlertRule,
  fetchAlertRuleTemplates,
} from "@/services/api/alert-rules";

interface Step5AlertRulesProps {
  deviceId: string;
  deviceType: string;
  onDone: () => void;
}

export function Step5AlertRules({ deviceId, deviceType, onDone }: Step5AlertRulesProps) {
  const [showForm, setShowForm] = useState(false);
  const [metricName, setMetricName] = useState("temperature");
  const [operator, setOperator] = useState<"GT" | "LT" | "GTE" | "LTE">("GT");
  const [threshold, setThreshold] = useState("80");
  const [severity, setSeverity] = useState("2");
  const [created, setCreated] = useState(false);
  const [error, setError] = useState("");

  const { data: templates = [] } = useQuery({
    queryKey: ["alert-rule-templates", deviceType],
    queryFn: () => fetchAlertRuleTemplates(deviceType),
  });
  const firstTemplate = useMemo(() => templates[0], [templates]);

  function loadDefaults() {
    if (!firstTemplate) return;
    setMetricName(firstTemplate.metric_name);
    setOperator(firstTemplate.operator);
    setThreshold(String(firstTemplate.threshold));
    setSeverity(String(firstTemplate.severity));
  }

  async function handleCreate() {
    setError("");
    try {
      if (firstTemplate) {
        await applyAlertRuleTemplates([firstTemplate.template_id]);
      } else {
        await createAlertRule({
          name: `${deviceId} ${metricName} threshold`,
          metric_name: metricName,
          operator,
          threshold: Number(threshold),
          severity: Number(severity),
          duration_seconds: 0,
          enabled: true,
          site_ids: null,
        });
      }
      setCreated(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to create rule");
    }
  }

  if (created) {
    return (
      <div className="space-y-4">
        <div className="rounded-md border border-green-500/30 bg-green-500/10 p-3 text-sm text-green-700 dark:text-green-300">
          Rule created successfully.
        </div>
        <div className="flex justify-end">
          <Button onClick={onDone}>Done</Button>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <p className="text-sm text-muted-foreground">
        Would you like to add an alert rule for this device?
      </p>
      {!showForm ? (
        <div className="flex gap-2">
          <Button variant="outline" onClick={onDone}>
            Skip
          </Button>
          <Button onClick={() => setShowForm(true)}>Add Rule</Button>
        </div>
      ) : (
        <div className="space-y-3 rounded-md border border-border p-3">
          {error && <div className="text-sm text-destructive">{error}</div>}
          <div className="grid gap-2">
            <Label>Metric Name</Label>
            <Input value={metricName} onChange={(event) => setMetricName(event.target.value)} />
          </div>
          <div className="grid gap-2 md:grid-cols-3">
            <div className="grid gap-1">
              <Label>Operator</Label>
              <select
                className="h-10 rounded-md border border-input bg-background px-3 text-sm"
                value={operator}
                onChange={(event) => setOperator(event.target.value as "GT" | "LT" | "GTE" | "LTE")}
              >
                <option value="GT">GT</option>
                <option value="LT">LT</option>
                <option value="GTE">GTE</option>
                <option value="LTE">LTE</option>
              </select>
            </div>
            <div className="grid gap-1">
              <Label>Threshold</Label>
              <Input
                type="number"
                value={threshold}
                onChange={(event) => setThreshold(event.target.value)}
              />
            </div>
            <div className="grid gap-1">
              <Label>Severity</Label>
              <select
                className="h-10 rounded-md border border-input bg-background px-3 text-sm"
                value={severity}
                onChange={(event) => setSeverity(event.target.value)}
              >
                <option value="1">Critical</option>
                <option value="2">Warning</option>
                <option value="3">Info</option>
              </select>
            </div>
          </div>
          <div className="flex justify-between">
            <Button type="button" variant="outline" onClick={loadDefaults} disabled={!firstTemplate}>
              Load Defaults for {deviceType || "device"}
            </Button>
            <div className="flex gap-2">
              <Button variant="outline" onClick={onDone}>
                Skip
              </Button>
              <Button onClick={handleCreate}>Create Rule</Button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
