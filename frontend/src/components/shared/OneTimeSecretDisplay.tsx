import { useMemo, useState } from "react";
import { Button } from "@/components/ui/button";

interface OneTimeSecretDisplayProps {
  label: string;
  value: string;
  filename?: string;
}

export function OneTimeSecretDisplay({ label, value, filename }: OneTimeSecretDisplayProps) {
  const [revealed, setRevealed] = useState(false);
  const [copied, setCopied] = useState(false);
  const masked = useMemo(() => "•".repeat(Math.max(16, value.length)), [value.length]);

  async function copyValue() {
    await navigator.clipboard.writeText(value);
    setCopied(true);
    window.setTimeout(() => setCopied(false), 2000);
  }

  function downloadEnv() {
    const key = label.toUpperCase().replace(/\s+/g, "_");
    const blob = new Blob([`${key}=${value}\n`], { type: "text/plain;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = filename ?? `${key.toLowerCase()}.env`;
    a.click();
    URL.revokeObjectURL(url);
  }

  return (
    <div className="space-y-2 rounded-md border border-border p-3">
      <div className="text-xs text-muted-foreground">{label}</div>
      <div className="rounded border border-border/60 bg-muted/40 p-2 font-mono text-sm break-all">
        {revealed ? value : masked}
      </div>
      <div className="flex gap-2">
        <Button size="sm" variant="outline" onClick={() => setRevealed((v) => !v)}>
          {revealed ? "Hide" : "Reveal"}
        </Button>
        <Button size="sm" variant="outline" onClick={copyValue}>
          {copied ? "Copied!" : "Copy"}
        </Button>
        {filename && (
          <Button size="sm" variant="outline" onClick={downloadEnv}>
            Download .env
          </Button>
        )}
      </div>
    </div>
  );
}
