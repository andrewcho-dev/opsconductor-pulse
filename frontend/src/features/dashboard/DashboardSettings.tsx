import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import { Settings, Pencil, Share2, Star, Lock, Plus } from "lucide-react";
import { toast } from "sonner";
import { toggleDashboardShare, updateDashboard } from "@/services/api/dashboards";
import type { Dashboard } from "@/services/api/dashboards";
import { getErrorMessage } from "@/lib/errors";

interface DashboardSettingsProps {
  dashboard: Dashboard;
  isEditing: boolean;
  onToggleEdit: () => void;
  onAddWidget: () => void;
}

export function DashboardSettings({
  dashboard,
  isEditing,
  onToggleEdit,
  onAddWidget,
}: DashboardSettingsProps) {
  const [renameOpen, setRenameOpen] = useState(false);
  const [newName, setNewName] = useState(dashboard.name);
  const [newDescription, setNewDescription] = useState(dashboard.description);
  const queryClient = useQueryClient();

  const renameMutation = useMutation({
    mutationFn: () =>
      updateDashboard(dashboard.id, {
        name: newName.trim(),
        description: newDescription.trim(),
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["dashboard", dashboard.id] });
      queryClient.invalidateQueries({ queryKey: ["dashboards"] });
      setRenameOpen(false);
      toast.success("Dashboard renamed");
    },
    onError: (err: Error) => {
      toast.error(getErrorMessage(err) || "Failed to rename dashboard");
    },
  });

  const shareMutation = useMutation({
    mutationFn: (shared: boolean) => toggleDashboardShare(dashboard.id, shared),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["dashboard", dashboard.id] });
      queryClient.invalidateQueries({ queryKey: ["dashboards"] });
      toast.success("Sharing updated");
    },
    onError: (err: Error) => {
      toast.error(getErrorMessage(err) || "Failed to update sharing");
    },
  });

  const defaultMutation = useMutation({
    mutationFn: () => updateDashboard(dashboard.id, { is_default: true }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["dashboard", dashboard.id] });
      queryClient.invalidateQueries({ queryKey: ["dashboards"] });
      toast.success("Default dashboard updated");
    },
    onError: (err: Error) => {
      toast.error(getErrorMessage(err) || "Failed to set default");
    },
  });

  if (!dashboard.is_owner) return null;

  return (
    <>
      <DropdownMenu>
        <DropdownMenuTrigger asChild>
          <Button variant="ghost" size="sm">
            <Settings className="h-4 w-4" />
          </Button>
        </DropdownMenuTrigger>
        <DropdownMenuContent align="end">
          <DropdownMenuItem onClick={onToggleEdit}>
            {isEditing ? (
              <>
                <Lock className="h-4 w-4 mr-2" />
                Lock Layout
              </>
            ) : (
              <>
                <Pencil className="h-4 w-4 mr-2" />
                Edit Layout
              </>
            )}
          </DropdownMenuItem>

          {isEditing && (
            <DropdownMenuItem onClick={onAddWidget}>
              <Plus className="h-4 w-4 mr-2" />
              Add Widget
            </DropdownMenuItem>
          )}

          <DropdownMenuSeparator />

          <DropdownMenuItem
            onClick={() => {
              setNewName(dashboard.name);
              setNewDescription(dashboard.description);
              setRenameOpen(true);
            }}
          >
            <Pencil className="h-4 w-4 mr-2" />
            Rename
          </DropdownMenuItem>

          {!dashboard.is_default && (
            <DropdownMenuItem onClick={() => defaultMutation.mutate()}>
              <Star className="h-4 w-4 mr-2" />
              Set as Default
            </DropdownMenuItem>
          )}

          <DropdownMenuSeparator />

          <div className="flex items-center justify-between px-2 py-2">
            <div className="flex items-center gap-2">
              <Share2 className="h-4 w-4" />
              <span className="text-sm">
                {dashboard.is_shared ? "Shared" : "Private"}
              </span>
            </div>
            <Switch
              checked={dashboard.is_shared}
              onCheckedChange={(checked) => shareMutation.mutate(checked)}
              disabled={shareMutation.isPending}
            />
          </div>
          {dashboard.is_shared && (
            <p className="px-2 pb-2 text-xs text-muted-foreground">
              All team members can view this dashboard.
            </p>
          )}
        </DropdownMenuContent>
      </DropdownMenu>

      <Dialog open={renameOpen} onOpenChange={setRenameOpen}>
        <DialogContent className="sm:max-w-[400px]">
          <DialogHeader>
            <DialogTitle>Rename Dashboard</DialogTitle>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <Label>Name</Label>
              <Input
                value={newName}
                onChange={(e) => setNewName(e.target.value)}
                maxLength={100}
              />
            </div>
            <div className="space-y-2">
              <Label>Description</Label>
              <Input
                value={newDescription}
                onChange={(e) => setNewDescription(e.target.value)}
                maxLength={500}
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setRenameOpen(false)}>
              Cancel
            </Button>
            <Button
              onClick={() => renameMutation.mutate()}
              disabled={!newName.trim() || renameMutation.isPending}
            >
              Save
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
}

