import type { RuleCondition, RuleOperator } from "@/services/api/types";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

const OPERATORS: { value: RuleOperator; label: string }[] = [
  { value: "GT", label: "> greater than" },
  { value: "GTE", label: ">= greater than or equal" },
  { value: "LT", label: "< less than" },
  { value: "LTE", label: "<= less than or equal" },
];

interface Props {
  condition: RuleCondition;
  index: number;
  onChange: (index: number, condition: RuleCondition) => void;
  onRemove: (index: number) => void;
  canRemove: boolean;
}

export function ConditionRow({ condition, index, onChange, onRemove, canRemove }: Props) {
  const update = (patch: Partial<RuleCondition>) => {
    onChange(index, { ...condition, ...patch });
  };

  return (
    <div className="grid gap-2 md:grid-cols-[1fr_210px_120px_160px_auto]">
      <Input
        type="text"
        placeholder="metric_name"
        value={condition.metric_name}
        onChange={(event) => update({ metric_name: event.target.value })}
      />
      <Select
        value={condition.operator}
        onValueChange={(value) => update({ operator: value as RuleOperator })}
      >
        <SelectTrigger>
          <SelectValue />
        </SelectTrigger>
        <SelectContent>
          {OPERATORS.map((operator) => (
            <SelectItem key={operator.value} value={operator.value}>
              {operator.label}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
      <Input
        type="number"
        placeholder="threshold"
        value={condition.threshold}
        onChange={(event) => update({ threshold: Number(event.target.value || 0) })}
        step="any"
      />
      <Input
        type="number"
        min={1}
        placeholder="min (optional)"
        value={condition.duration_minutes ?? ""}
        onChange={(event) =>
          update({
            duration_minutes:
              event.target.value === "" ? null : Number.parseInt(event.target.value, 10),
          })
        }
        title="Duration in minutes (leave blank for instant)"
      />
      {canRemove ? (
        <Button type="button" variant="outline" onClick={() => onRemove(index)}>
          Remove
        </Button>
      ) : (
        <div />
      )}
    </div>
  );
}
