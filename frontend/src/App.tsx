import { useEffect } from "react";
import { RouterProvider } from "react-router-dom";
import { Providers } from "@/app/providers";
import { router } from "@/app/router";
import { registerPulseThemes } from "@/lib/charts/theme";
import { useUIStore } from "@/stores/ui-store";

// Register ECharts themes (runs once on module load)
registerPulseThemes();

function App() {
  useEffect(() => {
    const { theme, setTheme } = useUIStore.getState();
    setTheme(theme);
  }, []);

  return (
    <Providers>
      <RouterProvider router={router} />
    </Providers>
  );
}

export default App;
