import { useState } from "react";

import { useAssignOperatorUserTenant, useOperatorUser, useOrganizations } from "@/hooks/use-users";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

interface AssignTenantDialogProps {
  userId: string;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onAssigned: () => void;
}

export function AssignTenantDialog({
  userId,
  open,
  onOpenChange,
  onAssigned,
}: AssignTenantDialogProps) {
  const { data: user } = useOperatorUser(userId);
  const { data: orgsData } = useOrganizations();
  const assignMutation = useAssignOperatorUserTenant();

  const [tenantId, setTenantId] = useState("");

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!tenantId) return;
    try {
      await assignMutation.mutateAsync({ userId, tenantId });
      onAssigned();
    } catch {
      // mutation state shows error
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>Assign Tenant</DialogTitle>
        </DialogHeader>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="text-sm text-muted-foreground">
            Assigning tenant for user: <strong>{user?.username}</strong>
          </div>
          {user?.tenant_id && (
            <div className="text-sm">
              Current tenant: <code className="rounded bg-muted px-1">{user.tenant_id}</code>
            </div>
          )}
          <div className="space-y-2">
            <Label htmlFor="tenant">New Tenant</Label>
            <Select value={tenantId} onValueChange={setTenantId}>
              <SelectTrigger>
                <SelectValue placeholder="Select tenant..." />
              </SelectTrigger>
              <SelectContent>
                {orgsData?.organizations?.map((org) => (
                  <SelectItem key={org.id} value={org.alias || org.name}>
                    {org.alias || org.name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          {assignMutation.isError && (
            <div className="text-sm text-destructive">
              {(assignMutation.error as Error).message}
            </div>
          )}
          <DialogFooter>
            <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>
              Cancel
            </Button>
            <Button type="submit" disabled={!tenantId || assignMutation.isPending}>
              {assignMutation.isPending ? "Assigning..." : "Assign Tenant"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
