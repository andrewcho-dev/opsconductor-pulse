# Phase 92 — Frontend: On-Call Schedules UI

## New files
- `frontend/src/features/oncall/OncallSchedulesPage.tsx`
- `frontend/src/features/oncall/ScheduleModal.tsx`
- `frontend/src/features/oncall/TimelineView.tsx`
- `frontend/src/features/oncall/OverrideModal.tsx`
- `frontend/src/services/api/oncall.ts`

## API service: oncall.ts

```typescript
export interface OncallLayer {
  layer_id: number;
  name: string;
  rotation_type: 'daily' | 'weekly' | 'custom';
  shift_duration_hours: number;
  handoff_day: number;
  handoff_hour: number;
  responders: string[];
  layer_order: number;
}

export interface OncallSchedule {
  schedule_id: number;
  name: string;
  description?: string;
  timezone: string;
  layers: OncallLayer[];
  created_at: string;
}

export interface OncallOverride {
  override_id: number;
  layer_id?: number;
  responder: string;
  start_at: string;
  end_at: string;
  reason?: string;
}

export interface TimelineSlot {
  start: string;
  end: string;
  responder: string;
  layer_name: string;
  is_override: boolean;
}

export interface CurrentOncall {
  responder: string;
  layer: string;
  until: string;
}

export async function listSchedules(): Promise<{ schedules: OncallSchedule[] }>
export async function createSchedule(body: Partial<OncallSchedule>): Promise<OncallSchedule>
export async function updateSchedule(id: number, body: Partial<OncallSchedule>): Promise<OncallSchedule>
export async function deleteSchedule(id: number): Promise<void>
export async function getCurrentOncall(scheduleId: number): Promise<CurrentOncall>
export async function getTimeline(scheduleId: number, days?: number): Promise<{ slots: TimelineSlot[] }>
export async function listOverrides(scheduleId: number): Promise<{ overrides: OncallOverride[] }>
export async function createOverride(scheduleId: number, body: Omit<OncallOverride, 'override_id'>): Promise<OncallOverride>
export async function deleteOverride(scheduleId: number, overrideId: number): Promise<void>
```

## OncallSchedulesPage layout

```
PageHeader: "On-Call Schedules"   [New Schedule button]

List of schedule cards:

┌─────────────────────────────────────────────────────────┐
│ Engineering Primary                    [View] [Edit] [×] │
│ Timezone: America/New_York                               │
│ Now on-call: alice@company.com  (until Mon 09:00)        │
└─────────────────────────────────────────────────────────┘
```

Clicking "View" expands or navigates to the schedule detail with TimelineView.

## ScheduleModal (create / edit)

shadcn Dialog, two sections:

**Schedule details:**
- Name (text)
- Description (textarea)
- Timezone (select — common zones: UTC, America/New_York, America/Los_Angeles,
  Europe/London, Europe/Berlin, Asia/Tokyo, Asia/Singapore)

**Layers:**
- One or more layer cards, each with:
  - Layer name (text)
  - Rotation: Daily / Weekly (toggle)
  - Handoff: day of week (select Mon–Sun) + hour (0–23 number input)
  - Responders: ordered list of email/name inputs with drag handles
    (use simple up/down arrow buttons instead of drag-and-drop)
  - [+ Add Layer] button (max 3 layers)

## TimelineView component

Props: `scheduleId: number`

Shows a 14-day horizontal timeline:

```
Layer: Primary On-Call
Mon 10  Tue 11  Wed 12  Thu 13  Fri 14  Sat 15  Sun 16  Mon 17
[── alice ──────────────────────────────][── bob ─────────
```

Each responder block is a colored `<div>` sized proportionally to shift length.
Overrides shown in a different color (amber) with a small "override" badge.

Below the timeline: "Overrides" section with a table and [+ Add Override] button.

## OverrideModal

Fields:
- Who covers (text input — email or name)
- From (datetime-local input)
- To (datetime-local input)
- Reason (text, optional)

## Escalation Policy link

In `EscalationPolicyModal.tsx` (from Phase 88): add an optional
"On-Call Schedule" select field to each level row, populated from
`listSchedules()`. When selected, the level will use the current on-call
responder at notification time instead of the static email.

## Route + Sidebar

- Route `/oncall` in `router.tsx`
- Add "On-Call" link under Monitoring group in `AppSidebar.tsx`
  (below Notifications added in Phase 91)
