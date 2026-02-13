import { createBrowserRouter, Navigate, Outlet } from "react-router-dom";
import AppShell from "@/components/layout/AppShell";
import DashboardPage from "@/features/dashboard/DashboardPage";
import DeviceListPage from "@/features/devices/DeviceListPage";
import DeviceDetailPage from "@/features/devices/DeviceDetailPage";
import AlertListPage from "@/features/alerts/AlertListPage";
import AlertRulesPage from "@/features/alerts/AlertRulesPage";
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
import OperatorTenantsPage from "@/features/operator/OperatorTenantsPage";
import OperatorTenantDetailPage from "@/features/operator/OperatorTenantDetailPage";
import SubscriptionsPage from "@/features/operator/SubscriptionsPage";
import SubscriptionDetailPage from "@/features/operator/SubscriptionDetailPage";
import OperatorUsersPage from "@/features/operator/OperatorUsersPage";
import { SystemDashboard } from "@/features/operator/SystemDashboard";
import AuditLogPage from "@/features/operator/AuditLogPage";
import SettingsPage from "@/features/operator/SettingsPage";
import UsersPage from "@/features/users/UsersPage";
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
            { path: "devices", element: <DeviceListPage /> },
            { path: "devices/:deviceId", element: <DeviceDetailPage /> },
            { path: "alerts", element: <AlertListPage /> },
            { path: "alert-rules", element: <AlertRulesPage /> },
            { path: "activity-log", element: <ActivityLogPage /> },
            { path: "metrics", element: <MetricsPage /> },
            { path: "integrations/webhooks", element: <WebhookPage /> },
            { path: "integrations/snmp", element: <SnmpPage /> },
            { path: "integrations/email", element: <EmailPage /> },
            { path: "integrations/mqtt", element: <MqttPage /> },
            { path: "subscription", element: <SubscriptionPage /> },
            { path: "subscription/renew", element: <RenewalPage /> },
            { path: "users", element: <UsersPage /> },
          ],
        },
        // Operator routes
        {
          path: "operator",
          element: <RequireOperator />,
          children: [
            { index: true, element: <OperatorDashboard /> },
            { path: "devices", element: <OperatorDevices /> },
            { path: "tenants", element: <OperatorTenantsPage /> },
            { path: "tenants/:tenantId", element: <OperatorTenantDetailPage /> },
            { path: "users", element: <OperatorUsersPage /> },
            { path: "subscriptions", element: <SubscriptionsPage /> },
            { path: "subscriptions/:subscriptionId", element: <SubscriptionDetailPage /> },
            { path: "system", element: <SystemDashboard /> },
            { path: "audit-log", element: <AuditLogPage /> },
            { path: "settings", element: <SettingsPage /> },
          ],
        },
      ],
    },
  ],
  { basename: "/app" }
);
