import { BrowserRouter, Navigate, Route, Routes } from "react-router";
import { ThemeProvider, ScopeProvider } from "@opchub/console-ui";
import { UsersPage, TenantsPage, ProjectsPage, RolesPage } from "@opchub/console-admin";
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
      <ScopeProvider>
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
              {/* 平台管理（三平台共用共享包，按权限显隐） */}
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
