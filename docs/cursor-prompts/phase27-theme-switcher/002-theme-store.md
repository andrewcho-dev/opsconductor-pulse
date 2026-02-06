# Phase 27.2: Add Theme State to Store

## Task

Add theme state to the Zustand store with localStorage persistence.

## Modify ui-store.ts

**File:** `frontend/src/stores/ui-store.ts`

```typescript
import { create } from "zustand";
import { persist } from "zustand/middleware";

type Theme = "light" | "dark" | "system";

interface UIStoreState {
  // Existing WebSocket state
  wsStatus: "connected" | "connecting" | "disconnected";
  wsRetryCount: number;
  wsError: string | null;
  setWsStatus: (status: "connected" | "connecting" | "disconnected") => void;
  setWsRetryCount: (count: number) => void;
  setWsError: (error: string | null) => void;

  // New theme state
  theme: Theme;
  setTheme: (theme: Theme) => void;
  resolvedTheme: "light" | "dark";  // Actual applied theme (resolves "system")
}

function getSystemTheme(): "light" | "dark" {
  if (typeof window === "undefined") return "dark";
  return window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
}

function resolveTheme(theme: Theme): "light" | "dark" {
  return theme === "system" ? getSystemTheme() : theme;
}

function applyTheme(theme: "light" | "dark") {
  const root = document.documentElement;
  if (theme === "dark") {
    root.classList.add("dark");
  } else {
    root.classList.remove("dark");
  }
}

export const useUIStore = create<UIStoreState>()(
  persist(
    (set, get) => ({
      // Existing WebSocket state
      wsStatus: "disconnected",
      wsRetryCount: 0,
      wsError: null,
      setWsStatus: (status) => set({ wsStatus: status }),
      setWsRetryCount: (count) => set({ wsRetryCount: count }),
      setWsError: (error) => set({ wsError: error }),

      // Theme state
      theme: "system",
      resolvedTheme: getSystemTheme(),
      setTheme: (theme) => {
        const resolved = resolveTheme(theme);
        applyTheme(resolved);
        set({ theme, resolvedTheme: resolved });
      },
    }),
    {
      name: "pulse-ui-store",
      partialize: (state) => ({ theme: state.theme }),  // Only persist theme
      onRehydrateStorage: () => (state) => {
        // Apply theme after rehydration
        if (state) {
          const resolved = resolveTheme(state.theme);
          applyTheme(resolved);
          state.resolvedTheme = resolved;
        }
      },
    }
  )
);

// Listen for system theme changes
if (typeof window !== "undefined") {
  window.matchMedia("(prefers-color-scheme: dark)").addEventListener("change", (e) => {
    const state = useUIStore.getState();
    if (state.theme === "system") {
      const resolved = e.matches ? "dark" : "light";
      applyTheme(resolved);
      useUIStore.setState({ resolvedTheme: resolved });
    }
  });
}
```

## Verification

```bash
cd /home/opsconductor/simcloud/frontend && npm run build
```

## Files

| Action | File |
|--------|------|
| MODIFY | `frontend/src/stores/ui-store.ts` |
