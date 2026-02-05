import { RouterProvider } from "react-router-dom";
import { Providers } from "@/app/providers";
import { router } from "@/app/router";
import { registerPulseDarkTheme } from "@/lib/charts/theme";

// Register ECharts dark theme (runs once on module load)
registerPulseDarkTheme();

function App() {
  return (
    <Providers>
      <RouterProvider router={router} />
    </Providers>
  );
}

export default App;
