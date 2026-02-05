# Task 001: Vite + React + TypeScript + Tailwind + shadcn/ui

> **CURSOR: EXECUTE THIS TASK**
>
> Read the instructions below and implement them exactly.
> Create only the files listed in "Files to Create/Modify".
> RUN THE TESTS in the Test section. Do not proceed if tests fail.
> IMPORTANT: Do not commit until all tests pass.

---

## Context

OpsConductor-Pulse currently uses Jinja2 server-rendered templates. We are building a new React SPA frontend in a `frontend/` directory at the project root. This task creates the project scaffold with Vite, React 19, TypeScript, Tailwind CSS, and shadcn/ui.

**System info**:
- Node.js v20.20.0, npm 10.8.2 are available
- Project root: `/home/opsconductor/simcloud`
- The `frontend/` directory does NOT exist yet

**Read first**:
- `docs/cursor-prompts/phase18-react-foundation/INSTRUCTIONS.md` — overview and color reference

---

## Task

### 1.1 Create Vite + React + TypeScript project

Run in terminal:

```bash
cd /home/opsconductor/simcloud
npm create vite@latest frontend -- --template react-ts
cd frontend
npm install
```

Verify `npm run dev` starts without errors (Ctrl+C to stop).

### 1.2 Install Tailwind CSS with Vite plugin

```bash
cd /home/opsconductor/simcloud/frontend
npm install -D tailwindcss @tailwindcss/vite
```

Update `vite.config.ts` to include the Tailwind plugin AND configure the API proxy and path alias:

```typescript
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";
import path from "path";

export default defineConfig({
  plugins: [react(), tailwindcss()],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
  server: {
    port: 5173,
    proxy: {
      "/api": {
        target: "http://localhost:8080",
        changeOrigin: true,
      },
    },
  },
});
```

Update `tsconfig.json` (the one in `frontend/`, NOT `tsconfig.app.json`) to add path aliases. **Merge** these settings into the existing `compilerOptions`:

```json
{
  "compilerOptions": {
    "baseUrl": ".",
    "paths": {
      "@/*": ["./src/*"]
    }
  }
}
```

Also update `tsconfig.app.json` to add the same path aliases to its `compilerOptions`:

```json
{
  "compilerOptions": {
    "baseUrl": ".",
    "paths": {
      "@/*": ["./src/*"]
    }
  }
}
```

### 1.3 Set up CSS with Tailwind and dark theme

Replace `frontend/src/index.css` with the Tailwind import and OpsConductor dark theme CSS variables:

```css
@import "tailwindcss";

/* OpsConductor Pulse Dark Theme */
:root {
  --background: 240 33% 5%;
  --foreground: 0 0% 93%;
  --card: 240 28% 14%;
  --card-foreground: 0 0% 93%;
  --popover: 240 28% 14%;
  --popover-foreground: 0 0% 93%;
  --primary: 216 89% 76%;
  --primary-foreground: 240 33% 5%;
  --secondary: 240 30% 24%;
  --secondary-foreground: 0 0% 93%;
  --muted: 240 20% 18%;
  --muted-foreground: 0 0% 53%;
  --accent: 240 30% 24%;
  --accent-foreground: 0 0% 93%;
  --destructive: 4 90% 58%;
  --destructive-foreground: 0 0% 93%;
  --border: 0 0% 20%;
  --input: 0 0% 20%;
  --ring: 216 89% 76%;
  --radius: 0.5rem;
  --chart-1: 216 89% 76%;
  --chart-2: 168 44% 40%;
  --chart-3: 12 76% 61%;
  --chart-4: 32 87% 67%;
  --chart-5: 48 83% 66%;
  --sidebar-background: 240 28% 10%;
  --sidebar-foreground: 0 0% 93%;
  --sidebar-primary: 216 89% 76%;
  --sidebar-primary-foreground: 240 33% 5%;
  --sidebar-accent: 240 30% 20%;
  --sidebar-accent-foreground: 0 0% 93%;
  --sidebar-border: 0 0% 20%;
  --sidebar-ring: 216 89% 76%;
}

@theme inline {
  --color-background: hsl(var(--background));
  --color-foreground: hsl(var(--foreground));
  --color-card: hsl(var(--card));
  --color-card-foreground: hsl(var(--card-foreground));
  --color-popover: hsl(var(--popover));
  --color-popover-foreground: hsl(var(--popover-foreground));
  --color-primary: hsl(var(--primary));
  --color-primary-foreground: hsl(var(--primary-foreground));
  --color-secondary: hsl(var(--secondary));
  --color-secondary-foreground: hsl(var(--secondary-foreground));
  --color-muted: hsl(var(--muted));
  --color-muted-foreground: hsl(var(--muted-foreground));
  --color-accent: hsl(var(--accent));
  --color-accent-foreground: hsl(var(--accent-foreground));
  --color-destructive: hsl(var(--destructive));
  --color-destructive-foreground: hsl(var(--destructive-foreground));
  --color-border: hsl(var(--border));
  --color-input: hsl(var(--input));
  --color-ring: hsl(var(--ring));
  --color-sidebar-background: hsl(var(--sidebar-background));
  --color-sidebar-foreground: hsl(var(--sidebar-foreground));
  --color-sidebar-primary: hsl(var(--sidebar-primary));
  --color-sidebar-primary-foreground: hsl(var(--sidebar-primary-foreground));
  --color-sidebar-accent: hsl(var(--sidebar-accent));
  --color-sidebar-accent-foreground: hsl(var(--sidebar-accent-foreground));
  --color-sidebar-border: hsl(var(--sidebar-border));
  --color-sidebar-ring: hsl(var(--sidebar-ring));
  --color-chart-1: hsl(var(--chart-1));
  --color-chart-2: hsl(var(--chart-2));
  --color-chart-3: hsl(var(--chart-3));
  --color-chart-4: hsl(var(--chart-4));
  --color-chart-5: hsl(var(--chart-5));
  --radius-sm: calc(var(--radius) - 4px);
  --radius-md: calc(var(--radius) - 2px);
  --radius-lg: var(--radius);
  --radius-xl: calc(var(--radius) + 4px);
}

/* Status colors as utilities */
@utility status-online {
  color: #4caf50;
}
@utility status-stale {
  color: #ff9800;
}
@utility severity-critical {
  color: #f44336;
}
@utility severity-warning {
  color: #ff9800;
}
@utility severity-info {
  color: #64b5f6;
}

/* Base styles */
body {
  background-color: hsl(var(--background));
  color: hsl(var(--foreground));
  font-family: ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont,
    "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
}
```

Delete `frontend/src/App.css` — we won't use it.

### 1.4 Install shadcn/ui dependencies and configure

```bash
cd /home/opsconductor/simcloud/frontend
npm install class-variance-authority clsx tailwind-merge lucide-react
```

Create `frontend/components.json`:

```json
{
  "$schema": "https://ui.shadcn.com/schema.json",
  "style": "new-york",
  "rsc": false,
  "tsx": true,
  "aliases": {
    "components": "@/components",
    "utils": "@/lib/utils",
    "ui": "@/components/ui",
    "lib": "@/lib",
    "hooks": "@/hooks"
  },
  "tailwind": {
    "config": "",
    "css": "src/index.css",
    "baseColor": "zinc",
    "cssVariables": true
  }
}
```

Create `frontend/src/lib/utils.ts`:

```typescript
import { type ClassValue, clsx } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}
```

### 1.5 Install shadcn/ui components

Run each command from `/home/opsconductor/simcloud/frontend`:

```bash
npx shadcn@latest add button card badge input select dialog table skeleton tooltip separator dropdown-menu sheet
```

If the CLI asks questions, accept defaults. If it fails on any component, install them one at a time:

```bash
npx shadcn@latest add button
npx shadcn@latest add card
npx shadcn@latest add badge
# ... etc
```

If shadcn CLI fails entirely (version incompatibility), skip this step — the components can be added manually later. The build must still succeed.

Also install the sidebar component:

```bash
npx shadcn@latest add sidebar
```

### 1.6 Create project directory structure

Create these empty directories:

```bash
cd /home/opsconductor/simcloud/frontend/src
mkdir -p app
mkdir -p components/layout
mkdir -p components/shared
mkdir -p features/dashboard/widgets
mkdir -p features/devices
mkdir -p features/alerts
mkdir -p features/integrations
mkdir -p features/operator
mkdir -p services/api
mkdir -p services/websocket
mkdir -p services/auth
mkdir -p stores
mkdir -p hooks
mkdir -p lib/charts
```

### 1.7 Create minimal App.tsx

Replace `frontend/src/App.tsx` with:

```tsx
function App() {
  return (
    <div className="min-h-screen bg-background text-foreground flex items-center justify-center">
      <div className="text-center space-y-4">
        <h1 className="text-3xl font-bold text-primary">OpsConductor Pulse</h1>
        <p className="text-muted-foreground">React frontend initializing...</p>
      </div>
    </div>
  );
}

export default App;
```

Update `frontend/src/main.tsx` to import the CSS:

```tsx
import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import "./index.css";
import App from "./App.tsx";

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <App />
  </StrictMode>
);
```

### 1.8 Create .env file for development

Create `frontend/.env`:

```
VITE_KEYCLOAK_URL=http://localhost:8180
VITE_KEYCLOAK_REALM=pulse
VITE_KEYCLOAK_CLIENT_ID=pulse-ui
```

Add to `frontend/.gitignore` (append, don't replace):

```
.env.local
.env.*.local
```

### 1.9 Clean up Vite boilerplate

Delete these files if they exist:
- `frontend/src/App.css`
- `frontend/src/assets/react.svg`
- `frontend/public/vite.svg`

---

## Files to Create/Modify

| Action | Path | What |
|--------|------|------|
| CREATE | `frontend/` | Entire Vite + React project via `npm create vite` |
| MODIFY | `frontend/vite.config.ts` | Add Tailwind plugin, path alias, API proxy |
| MODIFY | `frontend/tsconfig.json` | Add `baseUrl` and `paths` for `@/` alias |
| MODIFY | `frontend/tsconfig.app.json` | Add `baseUrl` and `paths` for `@/` alias |
| REPLACE | `frontend/src/index.css` | Tailwind import + dark theme CSS variables |
| CREATE | `frontend/components.json` | shadcn/ui configuration |
| CREATE | `frontend/src/lib/utils.ts` | `cn()` utility |
| REPLACE | `frontend/src/App.tsx` | Minimal app component |
| REPLACE | `frontend/src/main.tsx` | Entry point with CSS import |
| CREATE | `frontend/.env` | Keycloak env vars |
| CREATE | `frontend/src/components/ui/*` | shadcn/ui generated components |
| CREATE | `frontend/src/` subdirectories | Project structure (empty dirs) |
| DELETE | `frontend/src/App.css` | Unused boilerplate |
| DELETE | `frontend/src/assets/react.svg` | Unused boilerplate |
| DELETE | `frontend/public/vite.svg` | Unused boilerplate |

---

## Test

### Step 1: Verify build

```bash
cd /home/opsconductor/simcloud/frontend && npm run build
```

Must succeed with zero errors. Warnings are OK.

### Step 2: Verify dev server starts

```bash
cd /home/opsconductor/simcloud/frontend && timeout 10 npm run dev 2>&1 || true
```

Should show `Local: http://localhost:5173/` in output.

### Step 3: Verify directory structure

```bash
ls -la /home/opsconductor/simcloud/frontend/src/components/ui/ | head -5
ls -d /home/opsconductor/simcloud/frontend/src/{app,features,services,stores,hooks,lib}
```

Both commands should succeed.

### Step 4: Verify existing backend tests still pass

```bash
cd /home/opsconductor/simcloud && python3 -m pytest tests/unit/ -v -x
```

All 395 tests must pass.

---

## Acceptance Criteria

- [ ] `frontend/` directory exists at project root
- [ ] `npm run build` succeeds
- [ ] `npm run dev` starts Vite dev server on port 5173
- [ ] Tailwind CSS configured with dark theme variables
- [ ] shadcn/ui components installed (button, card, badge, table, dialog, sidebar, etc.)
- [ ] Path alias `@/` resolves to `src/`
- [ ] API proxy configured: `/api/*` → `http://localhost:8080`
- [ ] Project directory structure created (app, features, services, stores, hooks, lib)
- [ ] `.env` file with Keycloak vars
- [ ] No Vite boilerplate files remaining (App.css, react.svg, vite.svg)
- [ ] All existing Python tests pass

---

## Commit

```
Scaffold React frontend with Vite, Tailwind, and shadcn/ui

New frontend/ directory with React 19 + TypeScript + Vite build.
Tailwind CSS with OpsConductor dark theme. shadcn/ui components
installed. API proxy to FastAPI backend. Path aliases configured.

Phase 18 Task 1: Vite React Scaffold
```
