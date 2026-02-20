import { useSearchParams } from "react-router-dom";
import { PageHeader } from "@/components/shared";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { usePermissions } from "@/services/auth";
import UsersPage from "./UsersPage";
import RolesPage from "@/features/roles/RolesPage";

export default function TeamHubPage({ embedded }: { embedded?: boolean }) {
  const [params, setParams] = useSearchParams();
  const { hasPermission } = usePermissions();
  const canManageRoles = hasPermission("users.roles");

  const tab = params.get("tab") ?? "members";
  const activeTab = tab === "roles" && !canManageRoles ? "members" : tab;

  return (
    <div className="space-y-4">
      {!embedded && (
        <PageHeader title="Team" description="Manage users and roles in your organization" />
      )}
      <Tabs value={activeTab} onValueChange={(v) => setParams({ tab: v }, { replace: true })}>
        <TabsList variant="line">
          <TabsTrigger value="members">Members</TabsTrigger>
          {canManageRoles && <TabsTrigger value="roles">Roles</TabsTrigger>}
        </TabsList>
        <TabsContent value="members" className="mt-4">
          <UsersPage embedded />
        </TabsContent>
        {canManageRoles && (
          <TabsContent value="roles" className="mt-4">
            <RolesPage embedded />
          </TabsContent>
        )}
      </Tabs>
    </div>
  );
}

export const Component = TeamHubPage;

