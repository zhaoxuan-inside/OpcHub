import { BrowserRouter, Navigate, Route, Routes } from "react-router";
import { ThemeProvider, ScopeProvider } from "@opchub/console-ui";
import { UsersPage, TenantsPage, ProjectsPage, RolesPage } from "@opchub/console-admin";
import { AppShell } from "./shell/AppShell";
import { LoginPage } from "./pages/LoginPage";
import { OverviewPage } from "./pages/OverviewPage";
import { AuditPage } from "./pages/AuditPage";
import { RunsPage } from "./pages/RunsPage";
import { MetricsPage } from "./pages/MetricsPage";
import { DebugPage } from "./pages/DebugPage";

export function App() {
  return (
    <ThemeProvider>
      <ScopeProvider>
        <BrowserRouter>
          <Routes>
            <Route path="/login" element={<LoginPage />} />
            <Route element={<AppShell />}>
              <Route index element={<Navigate to="/overview" replace />} />
              <Route path="/overview" element={<OverviewPage />} />
              <Route path="/audit" element={<AuditPage />} />
              <Route path="/runs" element={<RunsPage />} />
              <Route path="/metrics" element={<MetricsPage />} />
              <Route path="/debug" element={<DebugPage />} />
              <Route path="/platform/users" element={<UsersPage />} />
              <Route path="/platform/tenants" element={<TenantsPage />} />
              <Route path="/platform/projects" element={<ProjectsPage />} />
              <Route path="/platform/roles" element={<RolesPage />} />
            </Route>
          </Routes>
        </BrowserRouter>
      </ScopeProvider>
    </ThemeProvider>
  );
}
