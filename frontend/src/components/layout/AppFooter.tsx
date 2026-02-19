import packageJson from "../../../package.json";

export function AppFooter() {
  return (
    <footer className="flex h-7 shrink-0 items-center justify-between border-t border-border/50 px-6 text-xs text-muted-foreground/60">
      <span>OpsConductor Pulse v{packageJson.version}</span>
      <span>{new Date().getFullYear()} OpsConductor</span>
    </footer>
  );
}

