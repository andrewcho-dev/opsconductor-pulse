import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { ChevronDown, Plus, Share2, Star, Trash2 } from "lucide-react";
import {
  fetchDashboards,
  createDashboard,
  deleteDashboard,
  updateDashboard,
} from "@/services/api/dashboards";
import type { DashboardSummary } from "@/services/api/dashboards";

interface DashboardSelectorProps {
  activeDashboardId: number | null;
  onSelect: (id: number) => void;
}

export function DashboardSelector({ activeDashboardId, onSelect }: DashboardSelectorProps) {
  const [showCreateDialog, setShowCreateDialog] = useState(false);
  const [newName, setNewName] = useState("");
  const [newDescription, setNewDescription] = useState("");
  const queryClient = useQueryClient();

  const { data } = useQuery({
    queryKey: ["dashboards"],
    queryFn: fetchDashboards,
  });

  const dashboards = data?.dashboards ?? [];
  const activeDashboard = dashboards.find((d) => d.id === activeDashboardId);

  const createMutation = useMutation({
    mutationFn: () =>
      createDashboard({
        name: newName.trim(),
        description: newDescription.trim(),
      }),
    onSuccess: (result) => {
      queryClient.invalidateQueries({ queryKey: ["dashboards"] });
      onSelect(result.id);
      setShowCreateDialog(false);
      setNewName("");
      setNewDescription("");
    },
  });

  const deleteMutation = useMutation({
    mutationFn: (id: number) => deleteDashboard(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["dashboards"] });
      const remaining = dashboards.filter((d) => d.id !== activeDashboardId);
      if (remaining.length > 0) {
        onSelect(remaining[0].id);
      }
    },
  });

  const setDefaultMutation = useMutation({
    mutationFn: (id: number) => updateDashboard(id, { is_default: true }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["dashboards"] });
    },
  });

  function handleDelete(dashboard: DashboardSummary) {
    if (!dashboard.is_owner) return;
    if (confirm(`Delete dashboard "${dashboard.name}"? This cannot be undone.`)) {
      deleteMutation.mutate(dashboard.id);
    }
  }

  return (
    <>
      <DropdownMenu>
        <DropdownMenuTrigger asChild>
          <Button variant="outline" size="sm" className="gap-1">
            {activeDashboard?.name || "Select Dashboard"}
            <ChevronDown className="h-4 w-4" />
          </Button>
        </DropdownMenuTrigger>
        <DropdownMenuContent align="start" className="w-[280px]">
          {dashboards.filter((d) => !d.is_shared).length > 0 && (
            <>
              <div className="px-2 py-1.5 text-sm font-semibold text-muted-foreground">
                My Dashboards
              </div>
              {dashboards
                .filter((d) => !d.is_shared)
                .map((d) => (
                  <DropdownMenuItem
                    key={d.id}
                    onClick={() => onSelect(d.id)}
                    className="flex items-center justify-between"
                  >
                    <div className="flex items-center gap-2 truncate">
                      {d.is_default && (
                        <Star className="h-3 w-3 text-yellow-500 shrink-0" />
                      )}
                      <span className={d.id === activeDashboardId ? "font-medium" : ""}>
                        {d.name}
                      </span>
                    </div>
                    <div className="flex items-center gap-1 shrink-0">
                      <span className="text-sm text-muted-foreground">{d.widget_count}w</span>
                      {d.is_owner && !d.is_default && (
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            setDefaultMutation.mutate(d.id);
                          }}
                          className="p-0.5 hover:text-yellow-500"
                          title="Set as default"
                        >
                          <Star className="h-3 w-3" />
                        </button>
                      )}
                      {d.is_owner && (
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            handleDelete(d);
                          }}
                          className="p-0.5 hover:text-destructive"
                          title="Delete"
                        >
                          <Trash2 className="h-3 w-3" />
                        </button>
                      )}
                    </div>
                  </DropdownMenuItem>
                ))}
            </>
          )}

          {dashboards.filter((d) => d.is_shared).length > 0 && (
            <>
              <DropdownMenuSeparator />
              <div className="px-2 py-1.5 text-sm font-semibold text-muted-foreground">
                <Share2 className="inline h-3 w-3 mr-1" />
                Shared Dashboards
              </div>
              {dashboards
                .filter((d) => d.is_shared)
                .map((d) => (
                  <DropdownMenuItem
                    key={d.id}
                    onClick={() => onSelect(d.id)}
                    className="flex items-center justify-between"
                  >
                    <span className={d.id === activeDashboardId ? "font-medium" : ""}>
                      {d.name}
                    </span>
                    <span className="text-sm text-muted-foreground">{d.widget_count}w</span>
                  </DropdownMenuItem>
                ))}
            </>
          )}

          <DropdownMenuSeparator />
          <DropdownMenuItem onClick={() => setShowCreateDialog(true)}>
            <Plus className="h-4 w-4 mr-2" />
            New Dashboard
          </DropdownMenuItem>
        </DropdownMenuContent>
      </DropdownMenu>

      <Dialog open={showCreateDialog} onOpenChange={setShowCreateDialog}>
        <DialogContent className="sm:max-w-[400px]">
          <DialogHeader>
            <DialogTitle>Create Dashboard</DialogTitle>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <Label>Name</Label>
              <Input
                value={newName}
                onChange={(e) => setNewName(e.target.value)}
                placeholder="My Dashboard"
                maxLength={100}
              />
            </div>
            <div className="space-y-2">
              <Label>Description (optional)</Label>
              <Input
                value={newDescription}
                onChange={(e) => setNewDescription(e.target.value)}
                placeholder="Dashboard purpose..."
                maxLength={500}
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowCreateDialog(false)}>
              Cancel
            </Button>
            <Button
              onClick={() => createMutation.mutate()}
              disabled={!newName.trim() || createMutation.isPending}
            >
              {createMutation.isPending ? "Creating..." : "Create"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
}

