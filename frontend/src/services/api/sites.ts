import { apiGet } from "./client";

export interface SiteWithRollup {
  site_id: string;
  name: string;
  location: string | null;
  latitude: number | null;
  longitude: number | null;
  device_count: number;
  online_count: number;
  stale_count: number;
  offline_count: number;
  active_alert_count: number;
}

export interface SiteSummary {
  site: { site_id: string; name: string; location: string | null };
  devices: Array<{
    device_id: string;
    name: string;
    status: string;
    device_type: string | null;
    last_seen_at?: string | null;
  }>;
  active_alerts: Array<{
    id: number;
    alert_type: string;
    severity: number;
    summary: string;
    status: string;
    created_at?: string;
  }>;
  device_count: number;
  active_alert_count: number;
}

export async function fetchSites(): Promise<{ sites: SiteWithRollup[]; total: number }> {
  return apiGet("/customer/sites");
}

export async function fetchSiteSummary(siteId: string): Promise<SiteSummary> {
  return apiGet(`/customer/sites/${encodeURIComponent(siteId)}/summary`);
}
