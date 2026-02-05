import { createBrowserRouter, Navigate } from "react-router-dom";
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
import AuditLogPage from "@/features/operator/AuditLogPage";
import SettingsPage from "@/features/operator/SettingsPage";
import { useAuth } from "@/services/auth/AuthProvider";

function HomeRedirect() {
  const { isOperator } = useAuth();
  return <Navigate to={isOperator ? "/operator" : "/dashboard"} replace />;
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
        { path: "operator", element: <OperatorDashboard /> },
        { path: "operator/devices", element: <OperatorDevices /> },
        { path: "operator/audit-log", element: <AuditLogPage /> },
        { path: "operator/settings", element: <SettingsPage /> },
      ],
    },
  ],
  { basename: "/app" }
);
