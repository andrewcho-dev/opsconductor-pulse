import { createBrowserRouter, Navigate, Outlet } from "react-router-dom";
import AppShell from "@/components/layout/AppShell";
import DashboardPage from "@/features/dashboard/DashboardPage";
import GettingStartedPage from "@/features/fleet/GettingStartedPage";
import HomePage from "@/features/home/HomePage";
import AlertsHubPage from "@/features/alerts/AlertsHubPage";
import AnalyticsHubPage from "@/features/analytics/AnalyticsHubPage";
import RulesHubPage from "@/features/rules/RulesHubPage";
import DevicesHubPage from "@/features/devices/DevicesHubPage";
import DeviceDetailPage from "@/features/devices/DeviceDetailPage";
import DeviceGroupsPage from "@/features/devices/DeviceGroupsPage";
import { SensorListPage } from "@/features/devices/SensorListPage";
import SetupWizard from "@/features/devices/wizard/SetupWizard";
import BulkImportPage from "@/features/devices/BulkImportPage";
import SitesPage from "@/features/sites/SitesPage";
import ConnectionGuidePage from "@/features/fleet/ConnectionGuidePage";
import MqttTestClientPage from "@/features/fleet/MqttTestClientPage";
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
import SiteDetailPage from "@/features/sites/SiteDetailPage";
import TemplateDetailPage from "@/features/templates/TemplateDetailPage";
import JobsPage from "@/features/jobs/JobsPage";
import OtaCampaignDetailPage from "@/features/ota/OtaCampaignDetailPage";
import SettingsHubPage from "@/features/settings/SettingsHubPage";
import NotFoundPage from "@/features/NotFoundPage";
import { useAuth } from "@/services/auth/AuthProvider";

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
            { path: "rules", element: <RulesHubPage /> },
            { path: "devices", element: <DevicesHubPage /> },
            { path: "updates", element: <Navigate to="/devices?tab=campaigns" replace /> },
            { path: "fleet/getting-started", element: <GettingStartedPage /> },
            { path: "fleet/tools", element: <ConnectionGuidePage /> },
            { path: "fleet/mqtt-client", element: <MqttTestClientPage /> },
            { path: "sites", element: <SitesPage /> },
            { path: "sites/:siteId", element: <SiteDetailPage /> },
            { path: "templates", element: <Navigate to="/devices?tab=templates" replace /> },
            { path: "templates/:templateId", element: <TemplateDetailPage /> },
            { path: "devices/import", element: <BulkImportPage /> },
            { path: "devices/wizard", element: <SetupWizard /> },
            { path: "devices/:deviceId", element: <DeviceDetailPage /> },
            { path: "sensors", element: <SensorListPage /> },
            { path: "device-groups", element: <DeviceGroupsPage /> },
            { path: "device-groups/:groupId", element: <DeviceGroupsPage /> },
            { path: "map", element: <Navigate to="/devices?tab=map" replace /> },
            { path: "alert-rules", element: <Navigate to="/rules?tab=alert-rules" replace /> },
            { path: "escalation-policies", element: <Navigate to="/rules?tab=escalation" replace /> },
            { path: "oncall", element: <Navigate to="/rules?tab=oncall" replace /> },
            { path: "maintenance-windows", element: <Navigate to="/rules?tab=maintenance" replace /> },
            { path: "integrations", element: <Navigate to="/settings?tab=channels" replace /> },
            { path: "integrations/*", element: <Navigate to="/settings?tab=channels" replace /> },
            { path: "customer/integrations", element: <Navigate to="/settings?tab=channels" replace /> },
            { path: "customer/integrations/*", element: <Navigate to="/settings?tab=channels" replace /> },
            { path: "activity-log", element: <ActivityLogPage /> },
            { path: "metrics", element: <MetricsPage /> },
            { path: "delivery-log", element: <Navigate to="/settings?tab=delivery" replace /> },
            { path: "dead-letter", element: <Navigate to="/settings?tab=dead-letter" replace /> },
            { path: "jobs", element: <JobsPage /> },
            { path: "ota/campaigns", element: <Navigate to="/devices?tab=campaigns" replace /> },
            { path: "ota/campaigns/:campaignId", element: <OtaCampaignDetailPage /> },
            { path: "ota/firmware", element: <Navigate to="/devices?tab=firmware" replace /> },
            { path: "reports", element: <Navigate to="/analytics?tab=reports" replace /> },
            { path: "subscription", element: <Navigate to="/settings?tab=billing" replace /> },
            { path: "subscription/renew", element: <RenewalPage /> },
            { path: "notifications", element: <Navigate to="/settings?tab=channels" replace /> },
            { path: "billing", element: <Navigate to="/settings?tab=billing" replace /> },
            { path: "team", element: <Navigate to="/settings?tab=members" replace /> },
            { path: "users", element: <Navigate to="/settings?tab=members" replace /> },
            { path: "roles", element: <Navigate to="/settings?tab=roles" replace /> },
            { path: "settings", element: <SettingsHubPage /> },
            { path: "settings/general", element: <Navigate to="/settings?tab=general" replace /> },
            { path: "settings/billing", element: <Navigate to="/settings?tab=billing" replace /> },
            { path: "settings/notifications", element: <Navigate to="/settings?tab=channels" replace /> },
            { path: "settings/integrations", element: <Navigate to="/settings?tab=integrations" replace /> },
            { path: "settings/access", element: <Navigate to="/settings?tab=members" replace /> },
            { path: "settings/profile", element: <Navigate to="/settings?tab=profile" replace /> },
            { path: "settings/organization", element: <Navigate to="/settings?tab=general" replace /> },
            { path: "settings/carrier", element: <Navigate to="/settings?tab=integrations" replace /> },
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
