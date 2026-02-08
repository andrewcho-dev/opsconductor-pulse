import { createBrowserRouter, Navigate, Outlet } from "react-router-dom";
import AppShell from "@/components/layout/AppShell";
import DashboardPage from "@/features/dashboard/DashboardPage";
import DeviceListPage from "@/features/devices/DeviceListPage";
import DeviceDetailPage from "@/features/devices/DeviceDetailPage";
import AlertListPage from "@/features/alerts/AlertListPage";
import AlertRulesPage from "@/features/alerts/AlertRulesPage";
import WebhookPage from "@/features/integrations/WebhookPage";
import SnmpPage from "@/features/integrations/SnmpPage";
import EmailPage from "@/features/integrations/EmailPage";
import MqttPage from "@/features/integrations/MqttPage";
import OperatorDashboard from "@/features/operator/OperatorDashboard";
import OperatorDevices from "@/features/operator/OperatorDevices";
import OperatorTenantsPage from "@/features/operator/OperatorTenantsPage";
import OperatorTenantDetailPage from "@/features/operator/OperatorTenantDetailPage";
import { SystemDashboard } from "@/features/operator/SystemDashboard";
import AuditLogPage from "@/features/operator/AuditLogPage";
import SettingsPage from "@/features/operator/SettingsPage";
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

export const router = createBrowserRouter(
  [
    {
      path: "/",
      element: <AppShell />,
      children: [
        { index: true, element: <HomeRedirect /> },
        { path: "dashboard", element: <DashboardPage /> },
        { path: "devices", element: <DeviceListPage /> },
        { path: "devices/:deviceId", element: <DeviceDetailPage /> },
        { path: "alerts", element: <AlertListPage /> },
        { path: "alert-rules", element: <AlertRulesPage /> },
        { path: "integrations/webhooks", element: <WebhookPage /> },
        { path: "integrations/snmp", element: <SnmpPage /> },
        { path: "integrations/email", element: <EmailPage /> },
        { path: "integrations/mqtt", element: <MqttPage /> },
        // Operator routes
        {
          path: "operator",
          element: <RequireOperator />,
          children: [
            { index: true, element: <OperatorDashboard /> },
            { path: "devices", element: <OperatorDevices /> },
            { path: "tenants", element: <OperatorTenantsPage /> },
            { path: "tenants/:tenantId", element: <OperatorTenantDetailPage /> },
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
