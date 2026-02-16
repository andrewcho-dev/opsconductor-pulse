import { useMemo } from "react";
import { Checkbox } from "@/components/ui/checkbox";
import { Label } from "@/components/ui/label";
import type { Permission } from "@/services/api/roles";

interface PermissionGridProps {
  permissions: Permission[];
  selectedIds: Set<number>;
  onChange: (ids: Set<number>) => void;
  disabled?: boolean;
}

export function PermissionGrid({ permissions, selectedIds, onChange, disabled }: PermissionGridProps) {
  const grouped = useMemo(() => {
    const map = new Map<string, Permission[]>();
    for (const p of permissions) {
      const list = map.get(p.category) || [];
      list.push(p);
      map.set(p.category, list);
    }
    return Array.from(map.entries()).sort(([a], [b]) => a.localeCompare(b));
  }, [permissions]);

  const togglePermission = (id: number) => {
    const next = new Set(selectedIds);
    if (next.has(id)) next.delete(id);
    else next.add(id);
    onChange(next);
  };

  const toggleCategory = (permsInCategory: Permission[]) => {
    const next = new Set(selectedIds);
    const allSelected = permsInCategory.every((p) => next.has(p.id));
    for (const p of permsInCategory) {
      if (allSelected) next.delete(p.id);
      else next.add(p.id);
    }
    onChange(next);
  };

  return (
    <div className="space-y-4">
      {grouped.map(([category, perms]) => {
        const allSelected = perms.every((p) => selectedIds.has(p.id));
        const anySelected = perms.some((p) => selectedIds.has(p.id));
        return (
          <div key={category} className="rounded-md border p-3">
            <div className="mb-2 flex items-center gap-2">
              <Checkbox
                checked={allSelected}
                aria-checked={anySelected && !allSelected ? "mixed" : undefined}
                disabled={disabled}
                onCheckedChange={() => toggleCategory(perms)}
              />
              <div className="text-sm font-medium">{category}</div>
            </div>
            <div className="space-y-2">
              {perms
                .slice()
                .sort((a, b) => a.action.localeCompare(b.action))
                .map((p) => (
                  <div key={p.id} className="flex items-start gap-3 rounded-md border p-2">
                    <Checkbox
                      checked={selectedIds.has(p.id)}
                      disabled={disabled}
                      onCheckedChange={() => togglePermission(p.id)}
                      className="mt-1"
                    />
                    <Label className="flex-1 cursor-pointer">
                      <div className="text-sm font-medium">{p.action}</div>
                      <div className="text-xs text-muted-foreground">{p.description}</div>
                    </Label>
                  </div>
                ))}
            </div>
          </div>
        );
      })}
    </div>
  );
}

