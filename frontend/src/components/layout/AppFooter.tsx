import packageJson from "../../../package.json";

export function AppFooter() {
  return (
    <footer className="flex h-8 shrink-0 items-center justify-between border-t border-border bg-card px-4 text-xs text-muted-foreground">
      <span>OpsConductor Pulse v{packageJson.version}</span>
      <span>{new Date().getFullYear()} OpsConductor</span>
    </footer>
  );
}

