# Prompt 001 — TV Mode

Read `frontend/src/features/operator/noc/NOCPage.tsx` and
`frontend/src/components/layout/AppShell.tsx` (or whatever wraps the sidebar).

## Add TV mode to NOCPage

TV mode = full-screen browser + hide sidebar + hide app header.

### Implementation in NOCPage:

```typescript
const [tvMode, setTvMode] = useState(false);

const toggleTvMode = useCallback(() => {
  if (!tvMode) {
    document.documentElement.requestFullscreen?.().catch(() => {});
    setTvMode(true);
  } else {
    document.exitFullscreen?.().catch(() => {});
    setTvMode(false);
  }
}, [tvMode]);

// Listen for Escape or F key to exit
useEffect(() => {
  const handler = (e: KeyboardEvent) => {
    if (e.key === 'Escape' && tvMode) setTvMode(false);
    if ((e.key === 'f' || e.key === 'F') && !e.metaKey && !e.ctrlKey) toggleTvMode();
  };
  window.addEventListener('keydown', handler);
  return () => window.removeEventListener('keydown', handler);
}, [tvMode, toggleTvMode]);

// Exit TV mode if browser exits fullscreen externally
useEffect(() => {
  const handler = () => {
    if (!document.fullscreenElement) setTvMode(false);
  };
  document.addEventListener('fullscreenchange', handler);
  return () => document.removeEventListener('fullscreenchange', handler);
}, []);
```

### Hide sidebar in TV mode:

Pass `tvMode` state via a context or use a CSS class on `document.body`:

```typescript
useEffect(() => {
  if (tvMode) {
    document.body.classList.add('noc-tv-mode');
  } else {
    document.body.classList.remove('noc-tv-mode');
  }
  return () => document.body.classList.remove('noc-tv-mode');
}, [tvMode]);
```

In the global CSS (`frontend/src/index.css` or `globals.css`):
```css
body.noc-tv-mode [data-sidebar],
body.noc-tv-mode aside,
body.noc-tv-mode nav {
  display: none !important;
}
body.noc-tv-mode main {
  margin-left: 0 !important;
  padding-left: 0 !important;
}
```

### TV mode button in NOCPage header:
Change the existing Maximize2 button to toggle `tvMode`:
```typescript
<button onClick={toggleTvMode} title="TV Mode (F)">
  {tvMode ? <Minimize2 className="h-4 w-4" /> : <Maximize2 className="h-4 w-4" />}
</button>
```

### TV mode overlay badge (top-right corner when in TV mode):
```typescript
{tvMode && (
  <div className="fixed top-2 right-2 z-50 bg-gray-800/80 text-gray-400 text-xs px-2 py-1 rounded">
    TV MODE — Press F to exit
  </div>
)}
```

## Acceptance Criteria
- [ ] F key toggles TV mode
- [ ] TV mode hides sidebar and nav
- [ ] Escape exits TV mode
- [ ] Browser fullscreen triggered on TV mode enter
- [ ] TV MODE badge visible in top-right when active
- [ ] `npm run build` passes
