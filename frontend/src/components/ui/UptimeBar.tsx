interface UptimeBarProps {
  uptimePct: number;
  label?: string;
}

export function UptimeBar({ uptimePct, label }: UptimeBarProps) {
  const bounded = Math.max(0, Math.min(100, uptimePct));
  const colorClass =
    bounded >= 99 ? "bg-green-500" : bounded >= 95 ? "bg-yellow-500" : "bg-red-500";
  return (
    <div className="space-y-1">
      {label && <div className="text-xs text-muted-foreground">{label}</div>}
      <div className="h-2 w-full rounded-full bg-muted">
        <div className={`h-2 rounded-full ${colorClass}`} style={{ width: `${bounded}%` }} />
      </div>
      <div className="text-xs font-medium">{bounded.toFixed(1)}%</div>
    </div>
  );
}
