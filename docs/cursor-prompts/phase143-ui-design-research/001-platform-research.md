# Platform-by-Platform UI Design Research

Research date: 2026-02-17

---

## 1. AWS IoT Core / SiteWise / TwinMaker (Cloudscape Design System)

AWS IoT services use the **Cloudscape Design System**, which is open-source and well-documented.

### Layout & Navigation

- **Sidebar**: Left-aligned, collapsible. Uses a "service navigation" pattern with a service identity (name + optional logo) at the top. The sidebar contains hierarchical link groups organized into sections with expandable/collapsible headers. It supports four hierarchical modes: simple flat list, organized with sections, organized with group sections, and nested expandable link groups.
- **Default behavior**: Sidebar is open by default on all pages except "create" and "edit" resource pages, where it collapses to give more room to forms.
- **Header**: AWS unified navigation bar sits at the very top (global across all AWS services). Below that, service-specific breadcrumbs and action bar. The top bar contains search, settings, help, and account icons.
- **Main content area**: Consumes 100% of available width and height. Uses a 12-column grid system internally. The AppLayout component has a CSS property `--awsui-min-content-width` set to 280px minimum.
- **Viewport containment**: Content scrolls within bounded regions. The AppLayout manages scroll containers -- sidebar, tools panel, and main content each scroll independently.

### Spacing & Density

- **Spacing scale** (4px base grid):
  - xxx-small: 2px
  - xx-small: 4px
  - x-small: 8px
  - small: 12px
  - medium: 16px
  - large: 20px
  - x-large: 24px
  - xx-large: 32px
  - xxx-large: 40px
- **Density**: Medium density -- not cramped, not spacious. AWS prioritizes clarity over information density. Smaller spacing inside components, larger spacing between components.
- **Card-to-card spacing**: Typically 20-24px (large to x-large).
- **Internal card padding**: 20px (large).

### Typography

- **Font**: Open Sans (primary), with Light/Normal/Bold/Heavy weights.
- **Heading hierarchy**:
  - h1: 24px/30px, Bold
  - h2: 20px/24px, Bold
  - h3: 18px/22px, Bold
  - h4: 16px/20px, Bold
  - h5: 14px/18px, Bold
- **Body text**: 14px/20px, Normal weight.
- **Small text**: 12px/16px, Normal weight. Used for metadata and secondary info.
- **Display text**: 42px/48px (Bold and Light variants) for large KPI values.
- **Minimum font size**: 12px (explicitly mandated by design system).

### Cards & Containers

- **Border radius**: 16px for containers and cards (explicitly larger for "different purpose" components). Smaller components (buttons, inputs, alerts) use a smaller consistent radius.
- **Borders vs shadows**: Drop shadows were replaced with thin 1px strokes on containers/cards/panels. Shadows reserved only for transient/overlapping elements (modals, popovers, dropdowns).
- **Border widths**: 1px for layout elements (containers, cards, dividers). 2px for interactive elements (buttons, tiles).
- **Section separation**: Light 1px dividers, background color differentiation, and spacing. Three fill strategies: dark fill (solid bg), light fill (lighter bg + darker border), outline only.

### Color System

- **Strategy**: Predominantly white/grayscale UI with colorful CTAs and status indicators.
- **Status colors**: Blue for primary actions. Red and green for resource status. Color is never the only means of conveying information (always paired with icons/text).
- **Background hierarchy**: White base > light gray sections > card surfaces.
- **Dark mode**: Fully supported. Darker backgrounds with brighter foreground. Design tokens swap automatically.

### Tables & Data

- Uses data table component with sortable columns, filtering, pagination.
- **Pagination**: Standard numbered pagination with items-per-page selector.
- **Actions**: Toolbar-based actions (above table), with inline actions via buttons or links in rows.

### Dashboard Patterns

- SiteWise dashboards use a resource explorer panel on the left for selecting assets/data.
- Widget-based dashboard with drag-and-drop.
- KPI cards and time-series charts arranged in configurable grid.

---

## 2. Azure IoT Hub / IoT Central (Fluent 2 Design System)

Azure IoT services use the **Fluent 2 Design System** and Azure IoT-specific Fluent CSS.

### Layout & Navigation

- **Sidebar**: Left pane with collapsible navigation. Expand/collapse via three-line hamburger icon at top. Items visible depend on user role.
- **Navigation sections**: Devices, Device groups, Device templates, Edge manifests, Data explorer, Dashboards, Jobs, Rules, Data export, Audit logs, Permissions, Application, Customization, IoT Central Home.
- **Header**: Top toolbar contains search, settings (language/theme), help dropdown, account/sign-out. Azure-standard header.
- **Main content**: Full-width below header, beside sidebar. Dashboard tiles use integer-unit positioning on a grid.
- **Viewport containment**: Page-level scroll with fixed header and collapsible sidebar.

### Spacing & Density

- **Spacing scale** (4px base grid, Fluent 2):
  - sizeNone: 0
  - size20: 2px
  - size40: 4px
  - size60: 6px
  - size80: 8px
  - size100: 10px
  - size120: 12px
  - size160: 16px
  - size200: 20px
  - size240: 24px
  - size280: 28px
  - size320: 32px
  - size360: 36px
  - size400: 40px
  - size480: 48px
  - size520: 52px
  - size560: 56px
- **Density**: Medium density. Azure targets enterprise users who need both clarity and reasonable information density.
- **Dashboard tiles**: Integer-based grid. Smallest tile is 1x1 unit. Line charts recommended at 2x2, markdown tiles at 1x1.

### Typography (Fluent 2 Web)

- **Font**: Segoe UI (system default).
- **Type ramp**:
  - Display: 68px/92px, Semibold
  - Large Title: 40px/52px, Semibold
  - Title 1: 32px/40px, Semibold
  - Title 2: 28px/36px, Semibold
  - Title 3: 24px/32px, Semibold
  - Subtitle 1: 20px/26px, Semibold
  - Subtitle 2: 16px/22px, Semibold
  - Body 1: 14px/20px (Regular, Semibold, Bold)
  - Caption 1: 12px/16px (Regular, Semibold, Bold)
  - Caption 2: 10px/14px (Regular, Semibold)
- **Body text**: 14px/20px standard.
- **Small text**: 12px for captions, 10px exists but rarely used.
- **Minimum touch target**: 44x44px (web), 48x48px (Android).

### Cards & Containers

- **Border radius**: Part of Fluent design tokens -- standardized globally. Typical corner radius for cards is 4-8px in Fluent 2.
- **Approach**: Subtle borders and background differentiation. Cards with slight elevation (shadow) in some contexts. Background color hierarchy drives containment.
- **CSS custom properties**: `--color-content-background-primary`, `--color-content-background-secondary` for layered backgrounds.

### Color System

- **Color tokens**: Global tokens (context-agnostic raw values) and alias tokens (semantic meaning).
- **Dark mode**: Full support. `baseLayerLuminance` switches between light and dark. CSS custom properties auto-switch.
- **Accent**: Blue primary. Green/red for status.
- **Background hierarchy**: Uses `--color-content-background-primary` and `--color-content-background-secondary` for layering.

### Tables & Data

- Standard Fluent DataGrid component.
- Row height aligned with touch targets (44-48px standard).
- Pagination with page size selector.
- Actions in toolbar + context menus.

### Dashboard Patterns

- Tile-based dashboards with integer grid sizing.
- KPI tiles, charts, markdown tiles, map tiles.
- Prebuilt template dashboards available.
- Accessibility: Line charts preferred over other chart types.

---

## 3. Google Cloud IoT / Operations Suite

Google Cloud IoT Core was discontinued in August 2023, but the design patterns from Google Cloud Console and Cloud Monitoring remain relevant.

### Layout & Navigation

- **Sidebar**: Left-aligned, collapsible. Icon-only collapsed state. Uses Google Material Design 3 patterns.
- **Navigation**: Hierarchical project/resource navigation. "Hamburger" menu to toggle sidebar. Pinnable navigation items.
- **Header**: Top bar with project selector, search (Ctrl+K), notifications bell, settings, account.
- **Content area**: Full width, responsive. Uses Material Design grid system.

### Spacing & Density

- **Material Design spacing**: 4px base grid, 8px common increment.
- **Density**: Google Cloud Console is medium-dense. Cloud Monitoring dashboards lean denser for NOC-style use.

### Typography

- **Font**: Google Sans / Roboto.
- **Body**: 14px standard for Cloud Console.
- **Headings**: Follow Material Design type scale.

### Cards & Containers

- **Border radius**: Material Design 3 uses graduated radius (8px small, 12px medium, 16px large, 28px extra-large). Cloud Console typically uses 8px for cards.
- **Containers**: Subtle elevation (shadow) + surface tinting in Material 3. Light borders for secondary containment.

### Color System

- Google uses a tonal palette system (Material 3). Primary, secondary, tertiary, error, neutral.
- Status: Green (OK), Yellow (warning), Red (critical).
- Dark mode: Full support via Material 3 dynamic color.

### Dashboard Patterns

- Cloud Monitoring uses widget-based dashboards with line charts, gauges, bar charts.
- Auto-layout and manual layout modes.
- MQL (Monitoring Query Language) for custom queries.

---

## 4. Losant IoT Platform

Losant is known for clean, developer-friendly dashboard UI.

### Layout & Navigation

- **Sidebar**: Vertical left sidebar (moved from top nav in 2019 redesign). Collapsible -- especially useful when editing workflows. Icon-based with text labels.
- **Navigation structure**: Main nav on far left, displays recent dashboards. Items grouped by application context. Keyboard shortcut for search (Option-L Mac, Alt-L Windows).
- **Header**: Application name, dashboard title, time selector, and global duration/resolution selector at top of dashboard views.
- **Content area**: Full width. Dashboards use block-based layout with drag-and-drop.

### Spacing & Density

- **Density**: Medium -- Losant targets a clean, uncluttered aesthetic while remaining functional for data visualization. Not as dense as Datadog or Grafana.
- **Dashboard blocks**: Each block represents a different data visualization type. Grid-based positioning with flexible sizing.

### Typography

- **Approach**: Clean sans-serif. Body text 14px. Headings use standard hierarchy.

### Cards & Containers

- **Style**: Clean card-based UI with subtle borders. Rounded corners (approximately 4-8px).
- **Dashboard blocks**: White/light card on slightly gray background. Clean separation.

### Color System

- Clean, professional palette. Blue primary accent.
- Status colors for device states.
- Dark dashboard backgrounds available for NOC/monitoring use.

### Dashboard Patterns

- Block-based dashboards (GPS History, Time Series, Gauge, Data Table, etc.).
- Template Library for reusable UI components.
- Experience Views for custom end-user dashboards with layouts, pages, and components.
- Clear separation between "builder" dashboards (internal) and "experience" dashboards (customer-facing).

---

## 5. ThingsBoard

ThingsBoard is the most feature-rich open-source IoT platform with a professional UI built on Angular Material.

### Layout & Navigation

- **Sidebar**: Left-side navigation with customizable menu. Supports sections and subitems. Icons with text labels. Draggable menu reordering. Custom menu scoping (all users, specific users, per-tenant).
- **Navigation items**: Home, Devices, Assets, Entity Views, Dashboards, Customers, Audit Logs, System Settings, and custom items.
- **Content area**: Full width. Dashboards use grid-based layout.

### Spacing & Density

- **Dashboard grid**: Default 24 columns. Minimum 10 columns, maximum 1000.
- **Widget margin**: Default 10px between widgets. Adjustable from 0 to 50px.
- **Margin type**: Controls whether margin applies to widget edges only or also to layout borders.
- **Mobile row height**: Default 70px per widget row (range: 5-200px).
- **Density**: Medium to dense, configurable. SCADA layouts use 0 margin for seamless connections.

### Typography

- Angular Material typography. Body 14px. Headings in standard Material hierarchy.
- Entities Table widget allows custom font size and text styling per column.

### Cards & Containers

- **Widget containers**: Configurable background color, text color, padding, margin, border radius, and shadow per widget.
- **Dashboard background**: Customizable color with transparency, supports background images.
- **Card styling**: Material Design card pattern with shadow. Configurable per widget.

### Color System

- Material Design color palette. Configurable per tenant (white-labeling).
- Status colors for device connectivity.
- Supports custom CSS per dashboard.

### Tables & Data

- **Entities Table Widget**: Highly configurable. Adjustable column widths (px or %). Custom row styling via JavaScript functions. Default pagination at 10 items per page.
- **Cell styling**: Per-cell conditional color based on value.
- **Pagination**: Configurable, can be hidden. Page size adjustable.

### Dashboard Patterns

- Three layout types: Default (responsive grid), SCADA (precise positioning, 0 margin), Divider (legacy left/right split).
- "Auto fill layout height" option to stretch widgets to fill viewport.
- Responsive breakpoints: Desktop (xl/lg), Laptop (md), Tablet (sm), Mobile (xs).
- Widget bundles: Cards, Charts, Gauges, Maps, SCADA symbols, Alarm widgets, Entity widgets.

---

## 6. Datadog Infrastructure Monitoring

Datadog is best-in-class for infrastructure/fleet dashboards. Uses the **DRUIDS** design system (Datadog Reusable User Interface Design System).

### Layout & Navigation

- **Sidebar**: Left-aligned, persistent. Five vertical zones:
  1. Top: Search bar + recently accessed pages (monitors, dashboards, notebooks)
  2. Middle: Product areas organized by icon categories (Infrastructure, APM, Digital Experience, Software Delivery, Security). Each category expands on hover to reveal sub-features.
  3. Core Features: Metrics and Logs
  4. Resources: Integrations, Bits AI, CoScreen
  5. Bottom: Admin, Help, Support
- **Navigation redesign (2024)**: Colors updated for greater contrast in both light/dark modes. More space for favorites with longer titles. Features ordered by usage patterns and relationships.
- **Header**: Minimal. Dashboard-specific controls (title, time range, variables) appear at top of content area, not in a separate header.
- **Content area**: Full width dashboard grid. 12-column system. "High density mode" arranges top/bottom halves side-by-side on wide screens.

### Spacing & Density

- **Density**: HIGH. Datadog is one of the densest UIs in this category. Designed for power users and NOC environments who need maximum data visibility.
- **Widget sizing**: Default 2 rows x 4 columns (medium). Small: 2x2. Large: 4x4.
- **Grid**: Responsive, snapping. Widgets auto-align and resize to fill width.
- **Card-to-card spacing**: Tight. Minimal gap between widgets to maximize data density.

### Typography

- **Font**: Sans-serif (system fonts).
- **Body**: 14px.
- **Icons**: System icons at 16px (recommended), min 16px, max 32px.
- **Emphasis**: Title-style capitalization for labels, sentence-style for placeholders.
- **Brand color**: #774aa4 (purple).

### Cards & Containers

- **Widget styling**: Clean cards with minimal borders. Subtle shadow or border depending on context.
- **Grouping**: Widget groups have color-coded headers for visual distinction.
- **Border radius**: Subtle rounding (~4px based on visual inspection).
- **Section separation**: Groups with colored header bars. Dashboard sections via widget grouping.

### Color System

- **Brand**: Purple (#774aa4).
- **UI Colors**: `#632ca6` (interactive purple), `#f6f6f6` (light bg), `#c7c7c7` (borders).
- **Status colors**: Standard red/yellow/green semantic. Diverging palettes for graphs (green-blue cool, yellow-orange warm).
- **Dark mode**: Full support. Ctrl+Opt+D shortcut. OS preference auto-follow. Updated sidebar colors for high contrast.
- **Graph palettes**: Classic, Cool, Warm, Viridis, Plasma.

### Tables & Data

- Sortable, filterable data tables.
- Stream widgets (log tables) recommended at minimum 6 columns wide (half dashboard).
- Inline actions and drill-down.
- High-density row presentation.

### Dashboard Patterns

- Two layout modes: "Dashboard" (new grid) vs legacy Timeboards/Screenboards.
- Widget grouping with color-coded headers.
- Template variables for dynamic filtering across widgets.
- TV mode for NOC displays.
- Time range selector at dashboard level.
- All widgets in groups recommended for consistent density-mode behavior.
- Minimum 4 columns for timeseries widgets, 6 for stream widgets.

---

## 7. Grafana

Grafana is the industry-standard dashboarding tool. Uses the **Saga** design system.

### Layout & Navigation

- **Sidebar**: Left-aligned. Icon-only collapsed state (~56px wide). Expands to full text+icon mode (~300px wide). "Mega-menu" pattern with expandable sections.
- **Navigation sections**: Home, Dashboards, Explore, Alerting, Connections, Administration. Each section expandable.
- **Header**: Dashboard-specific toolbar with title, time range picker, refresh rate, variables, share/save buttons.
- **Content area**: Full width. Panel grid with configurable row heights and column spans.

### Spacing & Density

- **Spacing base unit**: 8px (theme.spacing(1) = 8px).
- **Spacing scale** (multiplied):
  - 0.25 = 2px
  - 0.5 = 4px
  - 1 = 8px
  - 1.5 = 12px
  - 2 = 16px
  - 2.5 = 20px
  - 3 = 24px
  - 4 = 32px
  - 5 = 40px
  - 6 = 48px
  - 8 = 64px
  - 10 = 80px
- **Density**: HIGH. Grafana is designed for maximum data visibility. Panels are tightly packed. Minimal chrome around data.
- **Panel padding**: Historically debated -- users have requested both more and less padding. Current default provides small internal padding within panels.

### Typography

- **Font**: System fonts (Inter or platform default).
- **Body**: 14px.
- **Headings**: Organized hierarchically. Text component supports variant prop for visual styling independent of semantic heading level.
- **Small text used**: Yes, extensively for axis labels, legends, annotations.

### Cards & Containers

- **Border radius**: 2px (shape.radius.default). This is notably sharp compared to other platforms. Pill radius: 9999px. Circle: 100%.
- **Panel styling**: Dark background panels with subtle 1px borders (rgba borders with low opacity). No shadows on panels in default dark theme.
- **Section separation**: Row-based grouping. Collapsible rows. Background contrast between nested levels.

### Color System (Dark Theme)

- **Background hierarchy** (actual hex values from source):
  - Canvas (page bg): palette.gray05 = `#0b0c0e`
  - Primary (panel bg): palette.gray10 = `#141619`
  - Secondary/Elevated: palette.gray15 = `#202226`
- **Text colors**:
  - Primary: `rgb(204, 204, 220)` (light lavender-gray)
  - Secondary: `rgba(204, 204, 220, 0.65)`
  - Disabled: `rgba(204, 204, 220, 0.61)`
- **Border colors**:
  - Weak: `rgba(204, 204, 220, 0.12)`
  - Medium: `rgba(204, 204, 220, 0.20)`
  - Strong: `rgba(204, 204, 220, 0.30)`
- **Status colors**: 6 semantic groups: primary, secondary, info, success, warning, error. Each has main, shade, text, border, contrastText variants.
- **Action states**: Hover `rgba(204,204,220, 0.16)`, Selected `rgba(204,204,220, 0.12)`, Focus `rgba(204,204,220, 0.16)`.
- **Dark mode**: Default. Light mode also available. Theme switching per user preference.

### Tables & Data

- Table panel with sortable columns, pagination.
- High-density row display.
- Cell coloring based on thresholds.
- Inline sparklines within cells.

### Dashboard Patterns

- Row-based organization. Collapsible rows as section headers.
- Panels fill grid cells. 24-column grid default.
- Variables (template variables) for dynamic filtering.
- Time range picker is dashboard-global.
- Stat panels for KPI display (large text, configurable sizes).
- Mixed panel types on single dashboard (stat, graph, table, gauge, bar gauge, heatmap).
- TV/kiosk mode for NOC displays (cycles through dashboard pages).

---

Sources:
- [Cloudscape Spacing](https://cloudscape.design/foundation/visual-foundation/spacing/)
- [Cloudscape Typography](https://cloudscape.design/foundation/visual-foundation/typography/)
- [Cloudscape Visual Style](https://cloudscape.design/foundation/visual-foundation/visual-style/)
- [Cloudscape Colors](https://cloudscape.design/foundation/visual-foundation/colors/)
- [Cloudscape Side Navigation](https://cloudscape.design/patterns/general/service-navigation/side-navigation/)
- [Cloudscape Layout](https://cloudscape.design/foundation/visual-foundation/layout/)
- [Fluent 2 Layout](https://fluent2.microsoft.design/layout)
- [Fluent 2 Typography](https://fluent2.microsoft.design/typography)
- [Azure IoT Central UI Tour](https://learn.microsoft.com/en-us/azure/iot-central/core/overview-iot-central-tour)
- [Datadog Navigation Redesign](https://www.datadoghq.com/blog/datadog-navigation-redesign/)
- [Datadog Dashboard Guidelines](https://github.com/DataDog/effective-dashboards/blob/main/guidelines.md)
- [Datadog UI Extensions Design Guidelines](https://github.com/DataDog/apps/blob/master/docs/en/ui-extensions-design-guidelines.md)
- [Datadog Dark Mode](https://www.datadoghq.com/blog/introducing-datadog-darkmode/)
- [Grafana Border Radius](https://grafana.com/developers/saga/styling/border-radius)
- [Grafana Themes Guide](https://github.com/grafana/grafana/blob/main/contribute/style-guides/themes.md)
- [Grafana createColors.ts](https://github.com/grafana/grafana/blob/main/packages/grafana-data/src/themes/createColors.ts)
- [ThingsBoard Layouts](https://thingsboard.io/docs/user-guide/ui/layouts/)
- [ThingsBoard Entity Table Widget](https://thingsboard.io/docs/user-guide/ui/entity-table-widget/)
- [Losant UI Update](https://www.losant.com/blog/platform-update-20190227)
- [Losant Experience Views](https://docs.losant.com/experiences/views/)
- [Carbon Data Table Style](https://carbondesignsystem.com/components/data-table/style/)
- [Data Table UX Patterns](https://www.pencilandpaper.io/articles/ux-pattern-analysis-enterprise-data-tables)
