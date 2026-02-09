import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

interface MappingEditRowProps {
  rawMetric: string;
  multiplier: number | null;
  offset: number | null;
  onSave: (payload: { multiplier?: number | null; offset_value?: number | null }) => void;
  onRemove: () => void;
  isSaving?: boolean;
}

export default function MappingEditRow({
  rawMetric,
  multiplier,
  offset,
  onSave,
  onRemove,
  isSaving,
}: MappingEditRowProps) {
  const [editing, setEditing] = useState(false);
  const [localMultiplier, setLocalMultiplier] = useState(
    multiplier != null ? String(multiplier) : "1"
  );
  const [localOffset, setLocalOffset] = useState(
    offset != null ? String(offset) : "0"
  );

  function handleSave() {
    const mult = localMultiplier.trim() === "" ? null : Number(localMultiplier);
    const off = localOffset.trim() === "" ? null : Number(localOffset);
    if (localMultiplier.trim() !== "" && Number.isNaN(mult)) return;
    if (localOffset.trim() !== "" && Number.isNaN(off)) return;
    onSave({ multiplier: mult, offset_value: off });
    setEditing(false);
  }

  return (
    <tr>
      <td className="py-2 font-mono text-sm">{rawMetric}</td>
      <td className="py-2">
        {editing ? (
          <Input
            value={localMultiplier}
            onChange={(event) => setLocalMultiplier(event.target.value)}
            className="h-8 w-24"
          />
        ) : (
          <span>{multiplier ?? "—"}</span>
        )}
      </td>
      <td className="py-2">
        {editing ? (
          <Input
            value={localOffset}
            onChange={(event) => setLocalOffset(event.target.value)}
            className="h-8 w-24"
          />
        ) : (
          <span>{offset ?? "—"}</span>
        )}
      </td>
      <td className="py-2 text-right">
        {editing ? (
          <div className="flex justify-end gap-2">
            <Button size="sm" variant="outline" onClick={() => setEditing(false)}>
              Cancel
            </Button>
            <Button size="sm" onClick={handleSave} disabled={isSaving}>
              Save
            </Button>
          </div>
        ) : (
          <div className="flex justify-end gap-2">
            <Button size="sm" variant="outline" onClick={() => setEditing(true)}>
              Edit
            </Button>
            <Button size="sm" variant="destructive" onClick={onRemove} disabled={isSaving}>
              Remove
            </Button>
          </div>
        )}
      </td>
    </tr>
  );
}
