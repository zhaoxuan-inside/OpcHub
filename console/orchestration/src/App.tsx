import { BrowserRouter, Navigate, Route, Routes } from "react-router";
import { ThemeProvider } from "@opchub/console-ui";
import { AppShell } from "./shell/AppShell";
import { LoginPage } from "./pages/LoginPage";
import { OverviewPage } from "./pages/OverviewPage";
import { OperatorsPage } from "./pages/OperatorsPage";
import { ScenariosPage } from "./pages/ScenariosPage";
import { ReleasesPage } from "./pages/ReleasesPage";
import { ExperimentsPage } from "./pages/ExperimentsPage";
import { ConfigsPage } from "./pages/ConfigsPage";

export function App() {
  return (
    <ThemeProvider>
      <BrowserRouter>
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route element={<AppShell />}>
            <Route index element={<Navigate to="/overview" replace />} />
            <Route path="/overview" element={<OverviewPage />} />
            <Route path="/operators" element={<OperatorsPage />} />
            <Route path="/scenarios" element={<ScenariosPage />} />
            <Route path="/releases" element={<ReleasesPage />} />
            <Route path="/experiments" element={<ExperimentsPage />} />
            <Route path="/configs" element={<ConfigsPage />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </ThemeProvider>
  );
}
