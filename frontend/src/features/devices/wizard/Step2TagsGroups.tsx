import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { fetchDeviceGroups } from "@/services/api/devices";
import type { TagsGroupsData } from "./types";

interface Step2TagsGroupsProps {
  onNext: (data: TagsGroupsData) => void;
  onBack: () => void;
  initialData?: TagsGroupsData | null;
}

export function Step2TagsGroups({ onNext, onBack, initialData }: Step2TagsGroupsProps) {
  const [tagsText, setTagsText] = useState((initialData?.tags ?? []).join(", "));
  const [groupIds, setGroupIds] = useState<string[]>(initialData?.group_ids ?? []);
  const { data } = useQuery({
    queryKey: ["device-groups"],
    queryFn: fetchDeviceGroups,
  });
  const groups = useMemo(() => data?.groups ?? [], [data?.groups]);

  return (
    <div className="space-y-4">
      <div className="grid gap-2">
        <Label>Tags (comma-separated)</Label>
        <Input
          value={tagsText}
          onChange={(event) => setTagsText(event.target.value)}
          placeholder="production, floor-1"
        />
      </div>
      <div className="grid gap-2">
        <Label>Device Groups</Label>
        <div className="space-y-2 rounded-md border border-border p-3">
          {groups.length === 0 && (
            <div className="text-xs text-muted-foreground">No groups available.</div>
          )}
          {groups.map((group) => (
            <label key={group.group_id} className="flex items-center justify-between text-sm">
              <span>{group.name}</span>
              <input
                type="checkbox"
                checked={groupIds.includes(group.group_id)}
                onChange={(event) =>
                  setGroupIds((prev) =>
                    event.target.checked
                      ? [...new Set([...prev, group.group_id])]
                      : prev.filter((id) => id !== group.group_id)
                  )
                }
              />
            </label>
          ))}
        </div>
      </div>
      <div className="flex justify-between">
        <Button variant="outline" onClick={onBack}>
          Back
        </Button>
        <Button
          onClick={() =>
            onNext({
              tags: tagsText
                .split(",")
                .map((item) => item.trim())
                .filter(Boolean),
              group_ids: groupIds,
            })
          }
        >
          Next
        </Button>
      </div>
    </div>
  );
}
