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

export const router = createBrowserRouter(
  [
    {
      path: "/",
      element: <AppShell />,
      children: [
        { index: true, element: <Navigate to="/app/dashboard" replace /> },
        { path: "app/dashboard", element: <DashboardPage /> },
        { path: "app/devices", element: <DeviceListPage /> },
        { path: "app/devices/:deviceId", element: <DeviceDetailPage /> },
        { path: "app/alerts", element: <AlertListPage /> },
        { path: "app/alert-rules", element: <AlertRulesPage /> },
        { path: "app/integrations/webhooks", element: <WebhookPage /> },
        { path: "app/integrations/snmp", element: <SnmpPage /> },
        { path: "app/integrations/email", element: <EmailPage /> },
        { path: "app/integrations/mqtt", element: <MqttPage /> },
        // Operator routes
        { path: "app/operator", element: <OperatorDashboard /> },
        { path: "app/operator/devices", element: <OperatorDevices /> },
        { path: "app/operator/audit-log", element: <AuditLogPage /> },
        { path: "app/operator/settings", element: <SettingsPage /> },
      ],
    },
  ],
);
