# Prompt 003 — Service Health Topology Strip

Read `frontend/src/features/operator/SystemDashboard.tsx` to understand existing
service health data structures and `ComponentHealth` type.

## Create `frontend/src/features/operator/noc/ServiceTopologyStrip.tsx`

A horizontal strip showing the data pipeline as a visual flow diagram:

```
[MQTT Broker] ──► [Ingest Worker] ──► [TimescaleDB] ──► [Evaluator] ──► [Dispatcher] ──► [Delivery Worker]
                                            │
                                       [Keycloak]
                                       [PgBouncer]
```

Each service node:
- Colored border based on status (green=healthy, yellow=degraded, red=down, gray=unknown)
- Service name
- Latency in ms (if available)
- Status indicator dot

Arrow between nodes: `──►` rendered as a thin horizontal line with arrowhead.

### Implementation:

```typescript
interface ServiceNode {
  key: string;
  label: string;
  icon: LucideIcon;
  health?: ComponentHealth;
}

const PIPELINE: ServiceNode[][] = [
  // Main pipeline (top row)
  [
    { key: 'mqtt', label: 'MQTT', icon: Radio },
    { key: 'ingest', label: 'Ingest', icon: Upload },
    { key: 'postgres', label: 'TimescaleDB', icon: Database },
    { key: 'evaluator', label: 'Evaluator', icon: AlertTriangle },
    { key: 'dispatcher', label: 'Dispatcher', icon: Send },
    { key: 'delivery', label: 'Delivery', icon: Truck },
  ],
  // Support services (bottom row)
  [
    { key: 'keycloak', label: 'Keycloak', icon: Shield },
  ]
];
```

### Node card style:
```typescript
const nodeStyle = (status: string) => {
  const base = "flex flex-col items-center gap-1 px-3 py-2 rounded-lg border text-xs min-w-20";
  if (status === 'healthy') return `${base} border-green-500/50 bg-green-500/5 text-green-400`;
  if (status === 'degraded') return `${base} border-yellow-500/50 bg-yellow-500/5 text-yellow-400`;
  if (status === 'down') return `${base} border-red-500/50 bg-red-500/5 text-red-400`;
  return `${base} border-gray-600 bg-gray-800/50 text-gray-400`;
};
```

### Arrow between nodes:
```typescript
<div className="flex items-center text-gray-600 text-xs">──►</div>
```

### Data:
Fetch from GET /operator/system/health with `refetchInterval: 15000`.
Read `health.components[key]` for each node.

### Layout:
Full-width dark card `bg-gray-900 border-gray-700`.
Main pipeline row: `flex items-center gap-1 flex-wrap`.
Support services row below with smaller text.
Show last-checked timestamp top-right.

## Acceptance Criteria
- [ ] ServiceTopologyStrip.tsx with pipeline visualization
- [ ] Each node colored by health status
- [ ] Arrows between pipeline stages
- [ ] Latency shown on each node
- [ ] Refreshes every 15s
- [ ] `npm run build` passes
