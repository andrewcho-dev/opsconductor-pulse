/** Messages sent FROM client TO server */
export interface WsSubscribeMessage {
  action: "subscribe" | "unsubscribe";
  type: "alerts" | "device" | "fleet";
  device_id?: string;
}

/** Messages sent FROM server TO client */
export interface WsAlertMessage {
  type: "alerts";
  alerts: Array<{
    alert_id: number;
    tenant_id: string;
    device_id: string;
    alert_type: string;
    severity: number;
    summary: string;
    status: string;
    created_at: string;
    fingerprint: string;
    details: Record<string, unknown> | null;
    closed_at: string | null;
  }>;
}

export interface WsTelemetryMessage {
  type: "telemetry";
  device_id: string;
  data: {
    timestamp: string;
    metrics: Record<string, number | boolean>;
  };
}

export interface WsSubscribedMessage {
  type: "subscribed" | "unsubscribed";
  channel: string;
  device_id?: string;
}

export interface WsErrorMessage {
  type: "error";
  message: string;
}

export interface WsFleetSummaryMessage {
  type: "fleet_summary";
  data: {
    ONLINE: number;
    STALE: number;
    OFFLINE: number;
    total: number;
    active_alerts: number;
  };
}

export type WsServerMessage =
  | WsAlertMessage
  | WsTelemetryMessage
  | WsFleetSummaryMessage
  | WsSubscribedMessage
  | WsErrorMessage;

/** Message bus topics */
export type MessageTopic =
  | "alerts"
  | "fleet"
  | `telemetry:${string}`
  | "connection"
  | "error";
