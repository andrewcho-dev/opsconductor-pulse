import type { ReactNode } from "react"
import { Progress } from "@/components/ui/progress"

interface KpiCardProps {
  /** KPI label displayed at top */
  label: string
  /** The main value to display (big number) */
  value: string | number
  /** Optional: maximum value for progress bar (e.g., "0 / 1,000") */
  max?: number
  /** Optional: current numeric value for progress calculation */
  current?: number
  /** Optional: unit to append (e.g., "GB", "devices") */
  unit?: string
  /** Optional: small description text below the value */
  description?: string
  /** Optional: icon to show next to the label */
  icon?: ReactNode
  /** Optional: status color class for the value */
  valueClassName?: string
}

export function KpiCard({
  label,
  value,
  max,
  current,
  unit,
  description,
  icon,
  valueClassName,
}: KpiCardProps) {
  const progressPercent =
    max && current != null ? Math.min(100, Math.round((current / max) * 100)) : undefined

  return (
    <div className="rounded-lg border border-border bg-card p-4 space-y-2">
      <div className="flex items-center gap-2 text-sm text-muted-foreground">
        {icon}
        <span>{label}</span>
      </div>
      <div className={`text-2xl font-semibold ${valueClassName ?? ""}`}>
        {value}
        {unit && (
          <span className="text-sm font-normal text-muted-foreground ml-1">
            {unit}
          </span>
        )}
      </div>
      {progressPercent != null && <Progress value={progressPercent} className="h-1.5" />}
      {description && <p className="text-xs text-muted-foreground">{description}</p>}
    </div>
  )
}

