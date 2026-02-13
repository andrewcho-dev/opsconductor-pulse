import { useEffect, useState } from "react";

import { useChangeTenantUserRole, useTenantUser } from "@/hooks/use-users";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Label } from "@/components/ui/label";
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group";

interface ChangeRoleDialogProps {
  userId: string;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onChanged: () => void;
}

export function ChangeRoleDialog({
  userId,
  open,
  onOpenChange,
  onChanged,
}: ChangeRoleDialogProps) {
  const { data: user } = useTenantUser(userId);
  const changeMutation = useChangeTenantUserRole();

  const currentRole = user?.roles?.includes("tenant-admin") ? "tenant-admin" : "customer";
  const [role, setRole] = useState(currentRole);

  useEffect(() => {
    setRole(currentRole);
  }, [currentRole, open]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (role === currentRole) {
      onChanged();
      return;
    }
    try {
      await changeMutation.mutateAsync({ userId, role });
      onChanged();
    } catch {
      // mutation state shows error
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>Change Role</DialogTitle>
        </DialogHeader>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="text-sm text-muted-foreground">
            Changing role for:{" "}
            <strong>
              {[user?.first_name, user?.last_name].filter(Boolean).join(" ") || user?.username}
            </strong>
          </div>

          <RadioGroup value={role} onValueChange={setRole} className="space-y-3">
            <div className="flex items-start space-x-3 rounded-lg border p-3">
              <RadioGroupItem value="customer" id="customer" className="mt-1" />
              <Label htmlFor="customer" className="flex-1 cursor-pointer">
                <div className="font-medium">User</div>
                <div className="text-sm text-muted-foreground">
                  Can view devices, alerts, dashboards, and integrations.
                </div>
              </Label>
            </div>
            <div className="flex items-start space-x-3 rounded-lg border p-3">
              <RadioGroupItem value="tenant-admin" id="tenant-admin" className="mt-1" />
              <Label htmlFor="tenant-admin" className="flex-1 cursor-pointer">
                <div className="font-medium">Admin</div>
                <div className="text-sm text-muted-foreground">
                  Can manage team members, alert rules, integrations, and settings.
                </div>
              </Label>
            </div>
          </RadioGroup>

          {changeMutation.isError && (
            <div className="text-sm text-destructive">
              {(changeMutation.error as Error).message}
            </div>
          )}

          <DialogFooter>
            <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>
              Cancel
            </Button>
            <Button type="submit" disabled={changeMutation.isPending}>
              {changeMutation.isPending ? "Saving..." : "Save Role"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
