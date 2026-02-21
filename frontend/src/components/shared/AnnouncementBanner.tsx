import { useEffect, useMemo, useState } from "react";
import { X, Info, AlertTriangle, Flame } from "lucide-react";
import { useBroadcasts } from "@/features/home/useBroadcasts";

function useBannerDismissed() {
  const [dismissedIds, setDismissedIds] = useState<Set<string>>(() => {
    try {
      const raw = localStorage.getItem("banner_dismissed_ids");
      if (!raw) return new Set();
      return new Set(JSON.parse(raw));
    } catch {
      return new Set();
    }
  });

  const dismiss = (id: string) => {
    setDismissedIds((prev) => {
      const next = new Set(prev);
      next.add(id);
      try {
        localStorage.setItem("banner_dismissed_ids", JSON.stringify(Array.from(next)));
      } catch {
        // ignore
      }
      return next;
    });
  };

  return { dismissedIds, dismiss };
}

export function AnnouncementBanner() {
  const { data, isLoading } = useBroadcasts();
  const { dismissedIds, dismiss } = useBannerDismissed();

  const banner = useMemo(() => {
    if (!data || !data.length) return null;
    const sorted = [...data].sort((a, b) => {
      if (a.pinned && !b.pinned) return -1;
      if (!a.pinned && b.pinned) return 1;
      return new Date(b.created_at).getTime() - new Date(a.created_at).getTime();
    });
    return sorted.find((b) => (b as any).is_banner) ?? sorted[0];
  }, [data]);

  useEffect(() => {
    if (!banner) return;
    if (dismissedIds.has(banner.id)) {
      return;
    }
  }, [banner, dismissedIds]);

  if (isLoading || !banner || dismissedIds.has(banner.id)) return null;

  const tone =
    banner.type === "warning"
      ? "bg-amber-100 text-amber-900 border-amber-200"
      : banner.type === "update"
        ? "bg-emerald-100 text-emerald-900 border-emerald-200"
        : "bg-blue-100 text-blue-900 border-blue-200";
  const Icon = banner.type === "warning" ? AlertTriangle : banner.type === "update" ? Flame : Info;

  return (
    <div className={`border-b px-4 py-3 ${tone} flex items-start gap-3`}>
      <Icon className="h-4 w-4 mt-0.5" />
      <div className="flex-1 space-y-1">
        <div className="font-semibold">{banner.title}</div>
        <div className="text-sm text-muted-foreground/80">{banner.body}</div>
      </div>
      <button
        aria-label="Dismiss announcement"
        className="text-muted-foreground hover:text-foreground transition"
        onClick={() => dismiss(banner.id)}
      >
        <X className="h-4 w-4" />
      </button>
    </div>
  );
}
