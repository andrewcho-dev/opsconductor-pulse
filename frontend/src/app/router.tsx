import type { ReactNode } from "react";
import { createBrowserRouter, Navigate, Outlet } from "react-router-dom";
import AppShell from "@/components/layout/AppShell";
import DashboardPage from "@/features/dashboard/DashboardPage";
import DeviceListPage from "@/features/devices/DeviceListPage";
import DeviceDetailPage from "@/features/devices/DeviceDetailPage";
import DeviceGroupsPage from "@/features/devices/DeviceGroupsPage";
import SetupWizard from "@/features/devices/wizard/SetupWizard";
import BulkImportPage from "@/features/devices/BulkImportPage";
import AlertListPage from "@/features/alerts/AlertListPage";
import AlertRulesPage from "@/features/alerts/AlertRulesPage";
import MaintenanceWindowsPage from "@/features/alerts/MaintenanceWindowsPage";
import EscalationPoliciesPage from "@/features/escalation/EscalationPoliciesPage";
import NotificationChannelsPage from "@/features/notifications/NotificationChannelsPage";
import OncallSchedulesPage from "@/features/oncall/OncallSchedulesPage";
import ActivityLogPage from "@/features/audit/ActivityLogPage";
import MetricsPage from "@/features/metrics/MetricsPage";
import SubscriptionPage from "@/features/subscription/SubscriptionPage";
import RenewalPage from "@/features/subscription/RenewalPage";
import OperatorDashboard from "@/features/operator/OperatorDashboard";
import OperatorDevices from "@/features/operator/OperatorDevices";
import TenantListPage from "@/features/operator/TenantListPage";
import TenantHealthMatrix from "@/features/operator/TenantHealthMatrix";
import TenantDetailPage from "@/features/operator/TenantDetailPage";
import SubscriptionsPage from "@/features/operator/SubscriptionsPage";
import SubscriptionDetailPage from "@/features/operator/SubscriptionDetailPage";
import OperatorUsersPage from "@/features/operator/OperatorUsersPage";
import UserDetailPage from "@/features/operator/UserDetailPage";
import { SystemDashboard } from "@/features/operator/SystemDashboard";
import SystemMetricsPage from "@/features/operator/SystemMetricsPage";
import NOCPage from "@/features/operator/noc/NOCPage";
import AuditLogPage from "@/features/operator/AuditLogPage";
import SettingsPage from "@/features/operator/SettingsPage";
import UsersPage from "@/features/users/UsersPage";
import RolesPage from "@/features/roles/RolesPage";
import SitesPage from "@/features/sites/SitesPage";
import SiteDetailPage from "@/features/sites/SiteDetailPage";
import DeliveryLogPage from "@/features/delivery/DeliveryLogPage";
import ReportsPage from "@/features/reports/ReportsPage";
import JobsPage from "@/features/jobs/JobsPage";
import OtaCampaignsPage from "@/features/ota/OtaCampaignsPage";
import OtaCampaignDetailPage from "@/features/ota/OtaCampaignDetailPage";
import FirmwareListPage from "@/features/ota/FirmwareListPage";
import NotFoundPage from "@/features/NotFoundPage";
import { useAuth } from "@/services/auth/AuthProvider";
import { usePermissions } from "@/services/auth";

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

function RequirePermission({ permission, children }: { permission: string; children?: ReactNode }) {
  const { hasPermission, loading } = usePermissions();
  const { isOperator } = useAuth();

  // While permissions are loading, show nothing (prevents flash of redirect)
  if (loading && !isOperator) return null;

  if (!hasPermission(permission)) return <Navigate to="/dashboard" replace />;
  return children ? <>{children}</> : <Outlet />;
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
            { path: "devices/wizard", element: <SetupWizard /> },
            { path: "devices/:deviceId", element: <DeviceDetailPage /> },
            { path: "device-groups", element: <DeviceGroupsPage /> },
            { path: "device-groups/:groupId", element: <DeviceGroupsPage /> },
            { path: "alerts", element: <AlertListPage /> },
            { path: "alert-rules", element: <AlertRulesPage /> },
            { path: "maintenance-windows", element: <MaintenanceWindowsPage /> },
            { path: "escalation-policies", element: <EscalationPoliciesPage /> },
            { path: "notifications", element: <NotificationChannelsPage /> },
            { path: "oncall", element: <OncallSchedulesPage /> },
            { path: "integrations", element: <Navigate to="/notifications" replace /> },
            { path: "integrations/*", element: <Navigate to="/notifications" replace /> },
            { path: "customer/integrations", element: <Navigate to="/notifications" replace /> },
            { path: "customer/integrations/*", element: <Navigate to="/notifications" replace /> },
            { path: "activity-log", element: <ActivityLogPage /> },
            { path: "metrics", element: <MetricsPage /> },
            { path: "delivery-log", element: <DeliveryLogPage /> },
            { path: "jobs", element: <JobsPage /> },
            { path: "ota/campaigns", element: <OtaCampaignsPage /> },
            { path: "ota/campaigns/:campaignId", element: <OtaCampaignDetailPage /> },
            { path: "ota/firmware", element: <FirmwareListPage /> },
            { path: "reports", element: <ReportsPage /> },
            { path: "subscription", element: <SubscriptionPage /> },
            { path: "subscription/renew", element: <RenewalPage /> },
          ],
        },
        {
          element: <RequirePermission permission="users.read" />,
          children: [{ path: "users", element: <UsersPage /> }],
        },
        {
          element: <RequirePermission permission="users.roles" />,
          children: [{ path: "roles", element: <RolesPage /> }],
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
            { path: "users", element: <OperatorUsersPage /> },
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
        // 404 catch-all — must be last
        { path: "*", element: <NotFoundPage /> },
      ],
    },
  ],
  { basename: "/app" }
);
