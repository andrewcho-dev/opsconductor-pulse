import type { ReactNode } from "react";
import { createBrowserRouter, Navigate, Outlet } from "react-router-dom";
import AppShell from "@/components/layout/AppShell";
import SettingsLayout from "@/components/layout/SettingsLayout";
import DashboardPage from "@/features/dashboard/DashboardPage";
import GettingStartedPage from "@/features/fleet/GettingStartedPage";
import HomePage from "@/features/home/HomePage";
import AlertsHubPage from "@/features/alerts/AlertsHubPage";
import AnalyticsHubPage from "@/features/analytics/AnalyticsHubPage";
import UpdatesHubPage from "@/features/ota/UpdatesHubPage";
import NotificationsHubPage from "@/features/notifications/NotificationsHubPage";
import TeamHubPage from "@/features/users/TeamHubPage";
import DeviceListPage from "@/features/devices/DeviceListPage";
import DeviceDetailPage from "@/features/devices/DeviceDetailPage";
import DeviceGroupsPage from "@/features/devices/DeviceGroupsPage";
import { SensorListPage } from "@/features/devices/SensorListPage";
import FleetMapPage from "@/features/map/FleetMapPage";
import SetupWizard from "@/features/devices/wizard/SetupWizard";
import BulkImportPage from "@/features/devices/BulkImportPage";
import ActivityLogPage from "@/features/audit/ActivityLogPage";
import MetricsPage from "@/features/metrics/MetricsPage";
import RenewalPage from "@/features/subscription/RenewalPage";
import OperatorDashboard from "@/features/operator/OperatorDashboard";
import OperatorDevices from "@/features/operator/OperatorDevices";
import TenantListPage from "@/features/operator/TenantListPage";
import TenantHealthMatrix from "@/features/operator/TenantHealthMatrix";
import TenantDetailPage from "@/features/operator/TenantDetailPage";
import SubscriptionsPage from "@/features/operator/SubscriptionsPage";
import SubscriptionDetailPage from "@/features/operator/SubscriptionDetailPage";
import DeviceTiersPage from "@/features/operator/DeviceTiersPage";
import AccountTiersPage from "@/features/operator/AccountTiersPage";
import OperatorCarriersPage from "@/features/operator/OperatorCarriersPage";
import OperatorUsersPage from "@/features/operator/OperatorUsersPage";
import UserDetailPage from "@/features/operator/UserDetailPage";
import { SystemDashboard } from "@/features/operator/SystemDashboard";
import SystemMetricsPage from "@/features/operator/SystemMetricsPage";
import NOCPage from "@/features/operator/noc/NOCPage";
import AuditLogPage from "@/features/operator/AuditLogPage";
import SettingsPage from "@/features/operator/SettingsPage";
import CertificateOverviewPage from "@/features/operator/CertificateOverviewPage";
import SitesPage from "@/features/sites/SitesPage";
import SiteDetailPage from "@/features/sites/SiteDetailPage";
import TemplateListPage from "@/features/templates/TemplateListPage";
import TemplateDetailPage from "@/features/templates/TemplateDetailPage";
import JobsPage from "@/features/jobs/JobsPage";
import OtaCampaignDetailPage from "@/features/ota/OtaCampaignDetailPage";
import ProfilePage from "@/features/settings/ProfilePage";
import OrganizationPage from "@/features/settings/OrganizationPage";
import BillingPage from "@/features/settings/BillingPage";
import CarrierIntegrationsPage from "@/features/settings/CarrierIntegrationsPage";
import NotFoundPage from "@/features/NotFoundPage";
import { useAuth } from "@/services/auth/AuthProvider";
import { usePermissions } from "@/services/auth";

function HomeRedirect() {
  const { isOperator } = useAuth();
  return <Navigate to={isOperator ? "/operator" : "/home"} replace />;
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
            { path: "home", element: <HomePage /> },
            { path: "dashboard", element: <DashboardPage /> },
            { path: "alerts", element: <AlertsHubPage /> },
            { path: "analytics", element: <AnalyticsHubPage /> },
            { path: "updates", element: <UpdatesHubPage /> },
            { path: "fleet/getting-started", element: <GettingStartedPage /> },
            { path: "sites", element: <SitesPage /> },
            { path: "sites/:siteId", element: <SiteDetailPage /> },
            { path: "templates", element: <TemplateListPage /> },
            { path: "templates/:templateId", element: <TemplateDetailPage /> },
            { path: "devices", element: <DeviceListPage /> },
            { path: "devices/import", element: <BulkImportPage /> },
            { path: "devices/wizard", element: <SetupWizard /> },
            { path: "devices/:deviceId", element: <DeviceDetailPage /> },
            { path: "sensors", element: <SensorListPage /> },
            { path: "device-groups", element: <DeviceGroupsPage /> },
            { path: "device-groups/:groupId", element: <DeviceGroupsPage /> },
            { path: "map", element: <FleetMapPage /> },
            { path: "alert-rules", element: <Navigate to="/alerts?tab=rules" replace /> },
            { path: "escalation-policies", element: <Navigate to="/alerts?tab=escalation" replace /> },
            { path: "oncall", element: <Navigate to="/alerts?tab=oncall" replace /> },
            { path: "maintenance-windows", element: <Navigate to="/alerts?tab=maintenance" replace /> },
            { path: "integrations", element: <Navigate to="/settings/notifications" replace /> },
            { path: "integrations/*", element: <Navigate to="/settings/notifications" replace /> },
            { path: "customer/integrations", element: <Navigate to="/settings/notifications" replace /> },
            { path: "customer/integrations/*", element: <Navigate to="/settings/notifications" replace /> },
            { path: "activity-log", element: <ActivityLogPage /> },
            { path: "metrics", element: <MetricsPage /> },
            { path: "delivery-log", element: <Navigate to="/settings/notifications?tab=delivery" replace /> },
            { path: "dead-letter", element: <Navigate to="/settings/notifications?tab=dead-letter" replace /> },
            { path: "jobs", element: <JobsPage /> },
            { path: "ota/campaigns", element: <Navigate to="/updates?tab=campaigns" replace /> },
            { path: "ota/campaigns/:campaignId", element: <OtaCampaignDetailPage /> },
            { path: "ota/firmware", element: <Navigate to="/updates?tab=firmware" replace /> },
            { path: "reports", element: <Navigate to="/analytics?tab=reports" replace /> },
            { path: "subscription", element: <Navigate to="/settings/billing" replace /> },
            { path: "subscription/renew", element: <RenewalPage /> },
            // Settings route redirects (Phase 177)
            { path: "notifications", element: <Navigate to="/settings/notifications" replace /> },
            { path: "billing", element: <Navigate to="/settings/billing" replace /> },
            { path: "team", element: <Navigate to="/settings/access" replace /> },
            { path: "users", element: <Navigate to="/settings/access" replace /> },
            { path: "roles", element: <Navigate to="/settings/access?tab=roles" replace /> },
            {
              path: "settings",
              element: <SettingsLayout />,
              children: [
                { index: true, element: <Navigate to="/settings/general" replace /> },
                { path: "general", element: <OrganizationPage embedded /> },
                { path: "billing", element: <BillingPage embedded /> },
                { path: "notifications", element: <NotificationsHubPage embedded /> },
                { path: "integrations", element: <CarrierIntegrationsPage embedded /> },
                {
                  path: "access",
                  element: (
                    <RequirePermission permission="users.read">
                      <TeamHubPage embedded />
                    </RequirePermission>
                  ),
                },
                { path: "profile", element: <ProfilePage embedded /> },
                { path: "organization", element: <Navigate to="/settings/general" replace /> },
                { path: "carrier", element: <Navigate to="/settings/integrations" replace /> },
              ],
            },
          ],
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
            { path: "device-plans", element: <DeviceTiersPage /> },
            { path: "account-tiers", element: <AccountTiersPage /> },
            { path: "carriers", element: <OperatorCarriersPage /> },
            { path: "certificates", element: <CertificateOverviewPage /> },
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
