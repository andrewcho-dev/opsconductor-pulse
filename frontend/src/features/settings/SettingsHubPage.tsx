import { useSearchParams } from "react-router-dom";
import { PageHeader } from "@/components/shared";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { usePermissions } from "@/services/auth";
import OrganizationPage from "./OrganizationPage";
import BillingPage from "./BillingPage";
import NotificationChannelsPage from "@/features/notifications/NotificationChannelsPage";
import DeliveryLogPage from "@/features/delivery/DeliveryLogPage";
import DeadLetterPage from "@/features/messaging/DeadLetterPage";
import CarrierIntegrationsPage from "./CarrierIntegrationsPage";
import UsersPage from "@/features/users/UsersPage";
import RolesPage from "@/features/roles/RolesPage";
import ProfilePage from "./ProfilePage";

export default function SettingsHubPage() {
  const [params, setParams] = useSearchParams();
  const tab = params.get("tab") ?? "general";
  const { hasPermission } = usePermissions();
  const canViewTeam = hasPermission("users.read");
  const canManageRoles = hasPermission("users.roles");

  return (
    <div className="space-y-4">
      <PageHeader title="Settings" description="Manage your account and configuration" />
      <Tabs value={tab} onValueChange={(v) => setParams({ tab: v }, { replace: true })}>
        <TabsList variant="line">
          <TabsTrigger value="general">General</TabsTrigger>
          <TabsTrigger value="billing">Billing</TabsTrigger>
          <TabsTrigger value="channels">Channels</TabsTrigger>
          <TabsTrigger value="delivery">Delivery Log</TabsTrigger>
          <TabsTrigger value="dead-letter">Dead Letter</TabsTrigger>
          <TabsTrigger value="integrations">Integrations</TabsTrigger>
          {canViewTeam && <TabsTrigger value="members">Members</TabsTrigger>}
          {canViewTeam && canManageRoles && <TabsTrigger value="roles">Roles</TabsTrigger>}
          <TabsTrigger value="profile">Profile</TabsTrigger>
        </TabsList>
        <TabsContent value="general" className="mt-4">
          <OrganizationPage embedded />
        </TabsContent>
        <TabsContent value="billing" className="mt-4">
          <BillingPage embedded />
        </TabsContent>
        <TabsContent value="channels" className="mt-4">
          <NotificationChannelsPage embedded />
        </TabsContent>
        <TabsContent value="delivery" className="mt-4">
          <DeliveryLogPage embedded />
        </TabsContent>
        <TabsContent value="dead-letter" className="mt-4">
          <DeadLetterPage embedded />
        </TabsContent>
        <TabsContent value="integrations" className="mt-4">
          <CarrierIntegrationsPage embedded />
        </TabsContent>
        {canViewTeam && (
          <TabsContent value="members" className="mt-4">
            <UsersPage embedded />
          </TabsContent>
        )}
        {canViewTeam && canManageRoles && (
          <TabsContent value="roles" className="mt-4">
            <RolesPage embedded />
          </TabsContent>
        )}
        <TabsContent value="profile" className="mt-4">
          <ProfilePage embedded />
        </TabsContent>
      </Tabs>
    </div>
  );
}

export const Component = SettingsHubPage;
