import { useState } from "react";

import { useAssignOperatorUserRole, useOperatorUser } from "@/hooks/use-users";
import { Badge } from "@/components/ui/badge";
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

interface AssignRoleDialogProps {
  userId: string;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onAssigned: () => void;
}

const AVAILABLE_ROLES = [
  { value: "customer", label: "Customer", description: "Basic tenant access" },
  { value: "tenant-admin", label: "Tenant Admin", description: "Manage tenant users and settings" },
  { value: "operator", label: "Operator", description: "View all tenants" },
  { value: "operator-admin", label: "Operator Admin", description: "Full system administration" },
];

export function AssignRoleDialog({ userId, open, onOpenChange, onAssigned }: AssignRoleDialogProps) {
  const { data: user } = useOperatorUser(userId);
  const assignMutation = useAssignOperatorUserRole();
  const [role, setRole] = useState("");

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!role) return;
    try {
      await assignMutation.mutateAsync({ userId, role });
      onAssigned();
    } catch {
      // mutation state shows error
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>Assign Role</DialogTitle>
        </DialogHeader>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="text-sm text-muted-foreground">
            Assigning role for user: <strong>{user?.username}</strong>
          </div>
          {user?.roles && user.roles.length > 0 && (
            <div className="space-y-1">
              <div className="text-sm">Current roles:</div>
              <div className="flex flex-wrap gap-1">
                {user.roles.map((r) => (
                  <Badge key={r} variant="secondary">
                    {r}
                  </Badge>
                ))}
              </div>
            </div>
          )}
          <div className="space-y-2">
            <Label htmlFor="role">Add Role</Label>
            <Select value={role} onValueChange={setRole}>
              <SelectTrigger>
                <SelectValue placeholder="Select role..." />
              </SelectTrigger>
              <SelectContent>
                {AVAILABLE_ROLES.map((r) => (
                  <SelectItem key={r.value} value={r.value}>
                    {r.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            <div className="text-xs text-muted-foreground">
              {AVAILABLE_ROLES.find((r) => r.value === role)?.description || ""}
            </div>
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
            <Button type="submit" disabled={!role || assignMutation.isPending}>
              {assignMutation.isPending ? "Assigning..." : "Assign Role"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
