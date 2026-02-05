/** Messages sent FROM client TO server */
export interface WsSubscribeMessage {
  action: "subscribe" | "unsubscribe";
  type: "alerts" | "device";
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

export type WsServerMessage =
  | WsAlertMessage
  | WsTelemetryMessage
  | WsSubscribedMessage
  | WsErrorMessage;

/** Message bus topics */
export type MessageTopic =
  | "alerts"
  | `telemetry:${string}`
  | "connection"
  | "error";
