import { useCallback, useEffect, useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { PageHeader } from "@/components/shared";
import { Skeleton } from "@/components/ui/skeleton";
import { useAuth } from "@/services/auth/AuthProvider";
import { fetchDashboards, fetchDashboard } from "@/services/api/dashboards";
import { apiPost } from "@/services/api/client";
import { toast } from "sonner";
import { getErrorMessage } from "@/lib/errors";
import { DashboardBuilder } from "./DashboardBuilder";
import { DashboardSelector } from "./DashboardSelector";
import { DashboardSettings } from "./DashboardSettings";

export default function DashboardPage() {
  const { user } = useAuth();
  const queryClient = useQueryClient();
  const subtitle = user?.tenantId ? `Tenant: ${user.tenantId}` : "Real-time operational view";

  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [isEditing, setIsEditing] = useState(false);
  const [addWidgetOpen, setAddWidgetOpen] = useState(false);

  const bootstrapMutation = useMutation({
    mutationFn: () =>
      apiPost<{ id: number; created: boolean }>("/customer/dashboards/bootstrap", {}),
    onSuccess: (result) => {
      queryClient.invalidateQueries({ queryKey: ["dashboards"] });
      if (result.created && !selectedId) {
        setSelectedId(result.id);
      }
    },
    onError: (err: Error) => {
      toast.error(getErrorMessage(err) || "Failed to initialize dashboard");
    },
  });

  const { data: dashboardList, isLoading: listLoading } = useQuery({
    queryKey: ["dashboards"],
    queryFn: fetchDashboards,
  });

  useEffect(() => {
    if (!listLoading && dashboardList && dashboardList.dashboards.length === 0) {
      bootstrapMutation.mutate();
    }
  }, [listLoading, dashboardList?.dashboards?.length]);

  const defaultDashboard =
    dashboardList?.dashboards?.find((d) => d.is_default) || dashboardList?.dashboards?.[0];

  const activeDashboardId = selectedId ?? defaultDashboard?.id ?? null;

  const { data: dashboard, isLoading: dashLoading } = useQuery({
    queryKey: ["dashboard", activeDashboardId],
    queryFn: () => fetchDashboard(activeDashboardId!),
    enabled: activeDashboardId !== null,
  });

  useEffect(() => {
    // Preserve old behavior: switching dashboards exits edit mode and closes drawers.
    setIsEditing(false);
    setAddWidgetOpen(false);
  }, [activeDashboardId]);

  const handleToggleEdit = useCallback(() => {
    setIsEditing((prev) => !prev);
  }, []);

  const handleAddWidget = useCallback(() => {
    setIsEditing(true);
    setAddWidgetOpen(true);
  }, []);

  if (listLoading || bootstrapMutation.isPending) {
    return (
      <div className="space-y-4">
        <PageHeader title="Dashboard" description={subtitle} />
        <div className="grid gap-3 grid-cols-3">
          <Skeleton className="h-[200px]" />
          <Skeleton className="h-[200px]" />
          <Skeleton className="h-[200px]" />
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <PageHeader
        title={dashboard?.name || "Dashboard"}
        description={dashboard?.description || subtitle}
        action={
          <div className="flex items-center gap-2">
            <DashboardSelector
              activeDashboardId={activeDashboardId}
              onSelect={setSelectedId}
            />
            {dashboard && (
              <DashboardSettings
                dashboard={dashboard}
                isEditing={isEditing}
                onToggleEdit={handleToggleEdit}
                onAddWidget={handleAddWidget}
              />
            )}
          </div>
        }
      />

      {dashLoading ? (
        <div className="grid gap-3 grid-cols-3">
          <Skeleton className="h-[200px]" />
          <Skeleton className="h-[200px]" />
          <Skeleton className="h-[200px]" />
        </div>
      ) : dashboard ? (
        <DashboardBuilder
          dashboard={dashboard}
          canEdit={dashboard.is_owner}
          isEditing={isEditing}
          onToggleEdit={handleToggleEdit}
          onAddWidget={handleAddWidget}
          showAddWidget={addWidgetOpen}
          onShowAddWidgetChange={setAddWidgetOpen}
        />
      ) : (
        <div className="text-center py-8 text-muted-foreground">
          No dashboards available. Create one to get started.
        </div>
      )}
    </div>
  );
}
