import { useQuery } from "@tanstack/react-query";
import { apiGet } from "@/services/api/client";

export interface Broadcast {
  id: string;
  title: string;
  body: string;
  type: "info" | "warning" | "update";
  pinned: boolean;
  created_at: string;
}

export function useBroadcasts() {
  return useQuery({
    queryKey: ["broadcasts"],
    queryFn: () => apiGet<Broadcast[]>("/api/v1/customer/broadcasts"),
    staleTime: 5 * 60 * 1000,
  });
}
