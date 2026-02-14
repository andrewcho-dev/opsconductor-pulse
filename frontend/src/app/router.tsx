import { createBrowserRouter, Navigate, Outlet } from "react-router-dom";
import AppShell from "@/components/layout/AppShell";
import DashboardPage from "@/features/dashboard/DashboardPage";
import DeviceListPage from "@/features/devices/DeviceListPage";
import DeviceDetailPage from "@/features/devices/DeviceDetailPage";
import DeviceGroupsPage from "@/features/devices/DeviceGroupsPage";
import DeviceOnboardingWizard from "@/features/devices/wizard/DeviceOnboardingWizard";
import BulkImportPage from "@/features/devices/BulkImportPage";
import AlertListPage from "@/features/alerts/AlertListPage";
import AlertRulesPage from "@/features/alerts/AlertRulesPage";
import MaintenanceWindowsPage from "@/features/alerts/MaintenanceWindowsPage";
import EscalationPoliciesPage from "@/features/escalation/EscalationPoliciesPage";
import ActivityLogPage from "@/features/audit/ActivityLogPage";
import MetricsPage from "@/features/metrics/MetricsPage";
import WebhookPage from "@/features/integrations/WebhookPage";
import SnmpPage from "@/features/integrations/SnmpPage";
import EmailPage from "@/features/integrations/EmailPage";
import MqttPage from "@/features/integrations/MqttPage";
import SubscriptionPage from "@/features/subscription/SubscriptionPage";
import RenewalPage from "@/features/subscription/RenewalPage";
import OperatorDashboard from "@/features/operator/OperatorDashboard";
import OperatorDevices from "@/features/operator/OperatorDevices";
import TenantListPage from "@/features/operator/TenantListPage";
import TenantHealthMatrix from "@/features/operator/TenantHealthMatrix";
import TenantDetailPage from "@/features/operator/TenantDetailPage";
import SubscriptionsPage from "@/features/operator/SubscriptionsPage";
import SubscriptionDetailPage from "@/features/operator/SubscriptionDetailPage";
import UserListPage from "@/features/operator/UserListPage";
import UserDetailPage from "@/features/operator/UserDetailPage";
import { SystemDashboard } from "@/features/operator/SystemDashboard";
import SystemMetricsPage from "@/features/operator/SystemMetricsPage";
import NOCPage from "@/features/operator/noc/NOCPage";
import AuditLogPage from "@/features/operator/AuditLogPage";
import SettingsPage from "@/features/operator/SettingsPage";
import UsersPage from "@/features/users/UsersPage";
import SitesPage from "@/features/sites/SitesPage";
import SiteDetailPage from "@/features/sites/SiteDetailPage";
import DeliveryLogPage from "@/features/delivery/DeliveryLogPage";
import { useAuth } from "@/services/auth/AuthProvider";

function HomeRedirect() {
  const { isOperator } = useAuth();
  return <Navigate to={isOperator ? "/operator" : "/dashboard"} replace />;
}

function RequireOperator() {
  const { isOperator } = useAuth();
  if (!isOperator) return <Navigate to="/dashboard" replace />;
  return <Outlet />;
}

function RequireCustomer() {
  const { isCustomer, isOperator } = useAuth();
  if (isOperator && !isCustomer) return <Navigate to="/operator" replace />;
  if (!isCustomer) return <Navigate to="/" replace />;
  return <Outlet />;
}

function RequireTenantAdminOrOperator() {
  const { user } = useAuth();
  const roles = user?.realmAccess?.roles ?? [];
  const allowed =
    roles.includes("tenant-admin") ||
    roles.includes("operator") ||
    roles.includes("operator-admin");
  if (!allowed) return <Navigate to="/dashboard" replace />;
  return <Outlet />;
}

export const router = createBrowserRouter(
  [
    {
      path: "/",
      element: <AppShell />,
      children: [
        { index: true, element: <HomeRedirect /> },
        // Customer routes
        {
          element: <RequireCustomer />,
          children: [
            { path: "dashboard", element: <DashboardPage /> },
            { path: "sites", element: <SitesPage /> },
            { path: "sites/:siteId", element: <SiteDetailPage /> },
            { path: "devices", element: <DeviceListPage /> },
            { path: "devices/import", element: <BulkImportPage /> },
            { path: "devices/wizard", element: <DeviceOnboardingWizard /> },
            { path: "devices/:deviceId", element: <DeviceDetailPage /> },
            { path: "device-groups", element: <DeviceGroupsPage /> },
            { path: "device-groups/:groupId", element: <DeviceGroupsPage /> },
            { path: "alerts", element: <AlertListPage /> },
            { path: "alert-rules", element: <AlertRulesPage /> },
            { path: "maintenance-windows", element: <MaintenanceWindowsPage /> },
            { path: "escalation-policies", element: <EscalationPoliciesPage /> },
            { path: "activity-log", element: <ActivityLogPage /> },
            { path: "metrics", element: <MetricsPage /> },
            { path: "integrations/webhooks", element: <WebhookPage /> },
            { path: "delivery-log", element: <DeliveryLogPage /> },
            { path: "integrations/snmp", element: <SnmpPage /> },
            { path: "integrations/email", element: <EmailPage /> },
            { path: "integrations/mqtt", element: <MqttPage /> },
            { path: "subscription", element: <SubscriptionPage /> },
            { path: "subscription/renew", element: <RenewalPage /> },
          ],
        },
        {
          element: <RequireTenantAdminOrOperator />,
          children: [{ path: "users", element: <UsersPage /> }],
        },
        // Operator routes
        {
          path: "operator",
          element: <RequireOperator />,
          children: [
            { index: true, element: <OperatorDashboard /> },
            { path: "devices", element: <OperatorDevices /> },
            { path: "tenants", element: <TenantListPage /> },
            { path: "tenant-matrix", element: <TenantHealthMatrix /> },
            { path: "tenants/:tenantId", element: <TenantDetailPage /> },
            { path: "users", element: <UserListPage /> },
            { path: "users/:userId", element: <UserDetailPage /> },
            { path: "subscriptions", element: <SubscriptionsPage /> },
            { path: "subscriptions/:subscriptionId", element: <SubscriptionDetailPage /> },
            { path: "system", element: <SystemDashboard /> },
            { path: "system-metrics", element: <SystemMetricsPage /> },
            { path: "noc", element: <NOCPage /> },
            { path: "audit-log", element: <AuditLogPage /> },
            { path: "settings", element: <SettingsPage /> },
          ],
        },
      ],
    },
  ],
  { basename: "/app" }
);
