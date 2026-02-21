# Phase 105 — Frontend: Fleet Search Bar

## Context

Find the Fleet / Devices page. Likely:
- `frontend/src/pages/Fleet.jsx` or `Devices.jsx`
- Or search: `grep -rn "customer/devices\|/devices" frontend/src --include="*.jsx" --include="*.tsx" -l`

Read the file before making changes. Note how the device list is fetched.

## Change 1: Add search/filter state

At the top of the component, add state for filter values:

```jsx
const [search, setSearch] = React.useState("");
const [statusFilter, setStatusFilter] = React.useState("");
const [siteFilter, setSiteFilter] = React.useState("");
```

## Change 2: Pass filters to the API call

Find the fetch call for `/customer/devices`. Add query params:

```js
const params = new URLSearchParams();
if (search)       params.set("search", search);
if (statusFilter) params.set("status", statusFilter);
if (siteFilter)   params.set("site_id", siteFilter);
params.set("limit", "200");

const resp = await fetch(`/api/customer/devices?${params}`, {
  headers: { Authorization: `Bearer ${token}` },
});
```

If the fetch is in a `useEffect`, include `[search, statusFilter, siteFilter]`
in the dependency array so it re-fetches when filters change.

## Change 3: Add debounce to search input

To avoid firing a request on every keystroke:

```jsx
import { useDebouncedValue } from "../hooks/useDebouncedValue"; // create if needed

const [searchInput, setSearchInput] = React.useState("");
const search = useDebouncedValue(searchInput, 300);
```

If no debounce hook exists, create `frontend/src/hooks/useDebouncedValue.js`:

```js
import { useState, useEffect } from "react";

export function useDebouncedValue(value, delay) {
  const [debounced, setDebounced] = useState(value);
  useEffect(() => {
    const t = setTimeout(() => setDebounced(value), delay);
    return () => clearTimeout(t);
  }, [value, delay]);
  return debounced;
}
```

## Change 4: Render the search bar above the table

Add this JSX above the device table:

```jsx
<div className="fleet-search-bar" style={{ display: "flex", gap: "0.5rem", marginBottom: "1rem" }}>
  <input
    type="text"
    placeholder="Search devices..."
    value={searchInput}
    onChange={(e) => setSearchInput(e.target.value)}
    style={{ flex: 1, padding: "0.4rem 0.8rem" }}
  />
  <select
    value={statusFilter}
    onChange={(e) => setStatusFilter(e.target.value)}
  >
    <option value="">All statuses</option>
    <option value="online">Online</option>
    <option value="offline">Offline</option>
    <option value="maintenance">Maintenance</option>
  </select>
  {(search || statusFilter || siteFilter) && (
    <button
      onClick={() => { setSearchInput(""); setStatusFilter(""); setSiteFilter(""); }}
    >
      Clear
    </button>
  )}
</div>
```

Adjust `className` and inline styles to match the existing UI kit.

## Verify

```bash
npm run build --prefix frontend 2>&1 | tail -5
```

Expected: build succeeds.
