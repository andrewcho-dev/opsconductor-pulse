# Synthesis: Cross-Platform Patterns & Recommendations for OpsConductor-Pulse

---

## SYNTHESIS: Common Patterns Across All 7 Platforms

These are the patterns that virtually every platform implements, making them "industry standard" choices.

### 1. Layout & Navigation (Universal)

| Pattern | Consensus |
|---|---|
| **Sidebar position** | Left-aligned, always. No platform uses right or top-only navigation for primary nav. |
| **Sidebar collapsibility** | All platforms support collapsing. Most offer icon-only collapsed state. |
| **Sidebar grouping** | Navigation items are grouped into logical sections (not flat lists). Icons accompany every item. |
| **Header** | Thin global header (search, user menu, settings). Dashboard-specific controls (time range, variables) live at the top of the content area, not in the global header. |
| **Content scroll** | Sidebar and header are fixed/sticky. Main content area scrolls independently. |
| **12-column grid** | Cloudscape, Fluent, Datadog all use 12-column grids. ThingsBoard uses 24. Grafana uses 24. The 12-column grid is the web standard; 24 is used by dashboard-centric tools for finer control. |

### 2. Spacing (Universal)

| Pattern | Consensus |
|---|---|
| **Base unit** | 4px grid. Every platform (Cloudscape, Fluent, Material, Grafana) uses a 4px or 8px base unit. |
| **Body spacing** | 8px and 16px are the most commonly used spacing values (component gaps and section gaps). |
| **Card-to-card** | 8-16px for dashboard widgets, 16-24px for page-level card spacing. |
| **Internal card padding** | 16-24px. Never less than 12px, never more than 32px. |

### 3. Typography (Universal)

| Pattern | Consensus |
|---|---|
| **Body text size** | 14px. This is universal across all 7 platforms. |
| **Body line height** | 20px (1.43 ratio). Consistent across Cloudscape, Fluent, and others. |
| **Heading base** | h1 starts at 24px (Cloudscape) to 32px (Fluent Title 1). Most use 20-24px for page-level headings. |
| **Small text** | 12px is the universal "small" text size. Used for captions, metadata, table footnotes. |
| **Minimum text** | 10px exists in Fluent (Caption 2) but is rarely used. 12px is the practical minimum. |
| **Font weight** | Regular (400) for body, Semibold/Bold (600-700) for headings. Two weights cover 90% of UI. |
| **Font family** | System fonts or a clean sans-serif (Open Sans, Segoe UI, Roboto, Inter). |

### 4. Cards & Containers (Universal)

| Pattern | Consensus |
|---|---|
| **Containment strategy** | Borders > Shadows. AWS explicitly moved from shadows to borders. Grafana uses borders. Shadows are reserved for overlays/modals. |
| **Border weight** | 1px for containers. 2px reserved for interactive/emphasis elements. |
| **Border radius** | Wide range: Grafana 2px (sharp), Cloudscape 16px (very round), Fluent 4-8px (moderate). The mode is 4-8px. |
| **Background layering** | All platforms use 2-3 background tones: page surface (lightest/darkest), card/panel surface (one step lighter/darker), elevated surface (another step). |

### 5. Color System (Universal)

| Pattern | Consensus |
|---|---|
| **Status semantic** | Green = healthy/success. Red = critical/error. Yellow/Orange = warning. Blue = info/primary. |
| **Background grayscale** | UI is predominantly grayscale with status colors providing semantic meaning. |
| **Dark mode** | All 7 platforms support dark mode. All use CSS custom properties / design tokens for theme switching. |
| **Color never alone** | Color is always paired with icons or text (accessibility requirement all platforms share). |

### 6. Tables & Data (Universal)

| Pattern | Consensus |
|---|---|
| **Row height range** | Compact: 32-36px. Default: 40-48px. Comfortable: 48-56px. |
| **Column padding** | Minimum 16px per side (32px between columns). |
| **Pagination** | Numbered pagination with items-per-page selector. Page numbers + prev/next. |
| **Row lines** | Horizontal dividers only (no vertical lines, no zebra stripes in modern designs). |
| **Actions** | Toolbar for bulk actions above table. Inline actions via small buttons or overflow menu per row. |

### 7. Dashboard Patterns (Universal)

| Pattern | Consensus |
|---|---|
| **KPI cards** | Row of 3-4 stat cards at top of dashboard. Large prominent number + small label + trend indicator. |
| **Grid system** | Responsive grid with snap-to positioning. Widgets fill available width. |
| **Time range** | Global time range selector at dashboard level, affecting all widgets. |
| **Widget grouping** | Logical groups with headers/labels to organize related visualizations. |
| **TV/Kiosk mode** | Every monitoring platform supports a full-screen mode for NOC displays. |

---

## SYNTHESIS: What Differentiates the Leaders

| Platform | Distinctive Strength | Design Lesson |
|---|---|---|
| **Datadog** | Highest information density. Color-coded groups. High-density toggle. | For NOC/operator views, maximize density with togglable modes. |
| **Grafana** | 2px radius, dark-first design, extremely tight panels, row-based organization. | Dark mode as primary mode for monitoring. Minimal chrome. |
| **AWS Cloudscape** | Most mature spacing system. Clean token architecture. 16px card radius feels premium. | Well-defined spacing scale pays dividends in consistency. |
| **Azure Fluent** | Most complete typography ramp. 4px grid discipline. | Comprehensive type scale with semantic tokens enables design at scale. |
| **ThingsBoard** | Most configurable (24-1000 columns, 0-50px margins, per-widget styling). | Flexibility is a feature for IoT -- different deployments need different densities. |
| **Losant** | Cleanest "builder vs viewer" separation. Keyboard shortcuts for navigation. | Separate builder and consumer experiences. |

---

## RECOMMENDATIONS: Specific Design Values for OpsConductor-Pulse

Given the platform requirements:
- Customer dashboards (fleet overview, devices, alerts, rules)
- Operator/NOC dashboards (cross-tenant monitoring, command center)
- Configuration pages (escalation, notifications, on-call)
- Data-heavy tables (devices, alerts, telemetry)

### Spacing Scale

Adopt a **4px base grid** with the following semantic scale (matching Cloudscape/Fluent industry standard):

| Token | Value | Usage |
|---|---|---|
| `space-0` | 0px | No spacing |
| `space-0.5` | 2px | Micro adjustments (icon-to-text alignment) |
| `space-1` | 4px | Tight internal gaps (badge padding, inline items) |
| `space-2` | 8px | Default component internal padding, icon-to-label gap |
| `space-3` | 12px | Card internal padding (dense mode), compact form spacing |
| `space-4` | 16px | **Standard card padding, section-to-section in cards, form field gaps** |
| `space-5` | 20px | Card padding (comfortable), page section top margins |
| `space-6` | 24px | **Card-to-card gap, major section spacing** |
| `space-8` | 32px | Page-level section separation |
| `space-10` | 40px | Page top/bottom margins |

**Key decisions**:
- Card internal padding: **16px** (matches Cloudscape `medium`, Fluent `size160`)
- Card-to-card gap: **16px** (tighter than Cloudscape's 20-24px for better density -- matches the IoT monitoring use case)
- Page horizontal padding: **24px**
- Form field vertical gap: **16px**

### Border Radius

**Recommended: 8px** (`--radius: 0.5rem`)

Rationale:
- Grafana's 2px is too sharp for a multi-purpose platform (works for pure monitoring but feels cold for configuration pages).
- Cloudscape's 16px is too round for a dense data platform (wastes space, feels consumer-grade).
- 8px is the sweet spot used by Fluent and the majority of modern SaaS platforms. It conveys professionalism while softening harsh edges.

Current codebase already uses `--radius: 0.5rem` (8px) -- **this is correct, keep it**.

Derived values:
- `--radius-sm`: 4px (buttons, badges, small inputs)
- `--radius-md`: 6px (form inputs, smaller cards)
- `--radius-lg`: 8px (cards, containers, modals)
- `--radius-xl`: 12px (large hero cards, feature callouts)

### Heading Sizes

Adopt a 5-level heading scale matching the Cloudscape pattern (most appropriate for an enterprise IoT platform):

| Level | Size | Line Height | Weight | Usage |
|---|---|---|---|---|
| Page title (h1) | 24px (1.5rem) | 32px | Semibold (600) | Main page headings |
| Section title (h2) | 20px (1.25rem) | 28px | Semibold (600) | Major section headers within a page |
| Card title (h3) | 16px (1rem) | 24px | Semibold (600) | Card headers, widget titles |
| Subsection (h4) | 14px (0.875rem) | 20px | Semibold (600) | Sub-sections within cards, form section labels |
| Label (h5) | 12px (0.75rem) | 16px | Medium (500) | Small labels, metadata headers |
| **Body** | 14px (0.875rem) | 20px | Regular (400) | All body text |
| **Small/Caption** | 12px (0.75rem) | 16px | Regular (400) | Timestamps, metadata, table footnotes |
| **KPI value** | 32px (2rem) | 40px | Bold (700) | Large stat numbers on dashboards |

**Key decisions**:
- Page title at 24px (not 32px) -- for a dense data platform, 24px provides adequate hierarchy without consuming too much vertical space.
- Body at 14px -- universal standard.
- Small text at 12px -- minimum readable size. Never go below 12px.
- KPI display at 32px -- large enough to be read at a glance (NOC distance), small enough for 4 cards in a row.

### Card Padding

| Context | Padding | Rationale |
|---|---|---|
| **Dashboard widget (standard)** | 16px | Matches Cloudscape/Fluent standard. Good balance. |
| **Dashboard widget (dense/NOC)** | 12px | For operator views needing max info density. |
| **Configuration/form card** | 20px | Slightly more breathing room for forms and settings. |
| **KPI stat card** | 16px top/bottom, 20px left/right | KPI numbers need horizontal breathing room. |
| **Table container card** | 0px bottom (table extends to card edge), 16px top (for card header) | Tables look best when they extend to the card edges. |

### Background Color Strategy: Borders + Subtle Shading

Based on cross-platform research, adopt a **"borders primary, shading secondary"** approach:

**Light mode (current codebase values are close, refine slightly)**:
| Layer | Current HSL | Recommended Approach |
|---|---|---|
| Page background | `0 0% 100%` (white) | Change to very light gray: `hsl(220, 14%, 96%)` -- ~#F4F4F7. This is what Cloudscape, Datadog, and Azure all do. Pure white page bg is a mistake -- cards need contrast. |
| Card background | `0 0% 100%` (white) | Keep white. Cards pop against gray page bg. |
| Section/nested bg | N/A | Use `hsl(220, 14%, 98%)` for inset sections within cards. |
| Sidebar | `0 0% 98%` | Good. Keep slightly off-white. |
| Borders | `240 6% 90%` | Good. Subtle gray border. |

**Dark mode (current values are reasonable)**:
| Layer | Current HSL | Recommended Approach |
|---|---|---|
| Page background | `240 33% 5%` (~#0b0c10) | Good. Very dark. Similar to Grafana's `#0b0c0e`. |
| Card background | `240 20% 8%` (~#101318) | Good. One step lighter. Creates panel contrast. |
| Sidebar | `240 20% 6%` | Good. Slightly different from page bg for subtle distinction. |
| Borders | `240 10% 20%` | Good. Visible but not harsh. |

**Border vs shadow rule**: Use 1px borders on all cards and containers. Reserve shadows for: modals, dropdowns, popovers, and drag-in-progress states only. This matches the AWS/Grafana approach and performs better (no box-shadow rendering overhead for dozens of cards).

### Information Density

Implement **two density modes** (following Datadog's pattern):

| Mode | Target User | Characteristics |
|---|---|---|
| **Standard** | Customer dashboards, config pages | 16px card padding, 16px card gaps, 48px table rows, 14px body text, 20px card titles |
| **Dense/NOC** | Operator dashboards, command center | 12px card padding, 8px card gaps, 36px table rows, 13px body text, 14px card titles |

The toggle can be a user preference or page-level setting. NOC command center pages default to dense. Customer pages default to standard.

### Table Row Height

| Density | Row Height | Usage |
|---|---|---|
| **Compact** | 36px | NOC tables, alert feeds, high-volume data (matches Carbon "short" 32px rounded up for touch targets) |
| **Default** | 44px | Standard data tables (devices, rules, users) -- balances density with readability |
| **Comfortable** | 52px | Configuration tables, tables with multi-line content |

**Key decisions**:
- Default at 44px (not 48px) -- slightly denser than Carbon default, appropriate for IoT fleet tables which tend to have many rows.
- Column minimum padding: 12px horizontal (24px between columns).
- Header row: Same height as data rows + slightly heavier font weight (Semibold).
- Horizontal dividers only. No vertical column lines. No zebra striping -- use hover highlight instead.

### Minimum Text Size

**12px**. This is absolute. Enforced by:
- Cloudscape explicitly mandates 12px minimum.
- Every platform uses 12px as the smallest body text.
- 10px exists in Fluent (Caption 2) but only for extreme edge cases -- do not use it.

### Summary: Design Token Quick Reference

```
/* Spacing */
--space-1: 4px;
--space-2: 8px;
--space-3: 12px;
--space-4: 16px;   /* workhorse */
--space-5: 20px;
--space-6: 24px;   /* section gap */
--space-8: 32px;
--space-10: 40px;

/* Border radius */
--radius-sm: 4px;
--radius-md: 6px;
--radius-lg: 8px;   /* primary card radius */
--radius-xl: 12px;

/* Typography */
--text-xs: 12px;
--text-sm: 13px;    /* dense mode body */
--text-base: 14px;  /* standard body */
--text-lg: 16px;    /* card titles */
--text-xl: 20px;    /* section titles */
--text-2xl: 24px;   /* page titles */
--text-3xl: 32px;   /* KPI display */

/* Table */
--table-row-compact: 36px;
--table-row-default: 44px;
--table-row-comfortable: 52px;

/* Card */
--card-padding: 16px;
--card-padding-dense: 12px;
--card-gap: 16px;
--card-gap-dense: 8px;

/* Sidebar */
--sidebar-width-expanded: 256px;
--sidebar-width-collapsed: 48px;

/* Light backgrounds */
--bg-page: hsl(220, 14%, 96%);      /* #F1F2F6 */
--bg-card: hsl(0, 0%, 100%);         /* #FFFFFF */
--bg-inset: hsl(220, 14%, 98%);      /* #FAFAFC */
--bg-sidebar: hsl(220, 14%, 97%);    /* #F6F7F9 */

/* Dark backgrounds (current values are good) */
--bg-page-dark: hsl(240, 33%, 5%);
--bg-card-dark: hsl(240, 20%, 8%);
--bg-sidebar-dark: hsl(240, 20%, 6%);
```

### Key Changes From Current Codebase

Reviewing the current `/frontend/src/index.css`:

1. **Page background in light mode**: Change from pure white `0 0% 100%` to a warm/cool gray like `220 14% 96%`. This is the single highest-impact change -- it gives cards contrast against the page and matches every major platform.

2. **Border radius**: Current `--radius: 0.5rem` (8px) is already correct. No change needed.

3. **Status colors**: Current values `#4caf50` (online), `#ff9800` (warning), `#f44336` (critical), `#64b5f6` (info) are standard Material palette -- acceptable but slightly saturated. Consider desaturating slightly for dark mode legibility.

4. **Sidebar width**: Not defined as tokens currently. Should be extracted to tokens for the collapsed icon-only state (48px) and expanded state (256px).

5. **Density mode**: Not implemented. This is the biggest structural gap. Add a density context that can toggle spacing/padding/row-height tokens.

6. **Typography scale**: No text size tokens defined. Should add the scale above to the theme configuration.

---

Sources used in this synthesis:
- [Cloudscape Spacing](https://cloudscape.design/foundation/visual-foundation/spacing/)
- [Cloudscape Typography](https://cloudscape.design/foundation/visual-foundation/typography/)
- [Cloudscape Visual Style](https://cloudscape.design/foundation/visual-foundation/visual-style/)
- [Fluent 2 Layout](https://fluent2.microsoft.design/layout)
- [Fluent 2 Typography](https://fluent2.microsoft.design/typography)
- [Grafana Border Radius](https://grafana.com/developers/saga/styling/border-radius)
- [Grafana Themes](https://github.com/grafana/grafana/blob/main/contribute/style-guides/themes.md)
- [Grafana createColors.ts](https://github.com/grafana/grafana/blob/main/packages/grafana-data/src/themes/createColors.ts)
- [Datadog Navigation Redesign](https://www.datadoghq.com/blog/datadog-navigation-redesign/)
- [Datadog Effective Dashboards](https://github.com/DataDog/effective-dashboards/blob/main/guidelines.md)
- [Carbon Data Table Style](https://carbondesignsystem.com/components/data-table/style/)
- [Data Table UX Patterns](https://www.pencilandpaper.io/articles/ux-pattern-analysis-enterprise-data-tables)
- [ThingsBoard Layouts](https://thingsboard.io/docs/user-guide/ui/layouts/)
- [Azure IoT Central Tour](https://learn.microsoft.com/en-us/azure/iot-central/core/overview-iot-central-tour)
- [Losant Platform Update](https://www.losant.com/blog/platform-update-20190227)
- [Designing for Data Density](https://paulwallas.medium.com/designing-for-data-density-what-most-ui-tutorials-wont-teach-you-091b3e9b51f4)
- [IoT Dashboard Best Practices](https://flatlogic.com/blog/how-to-build-an-iot-dashboard/)
