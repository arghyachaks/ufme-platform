import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import { AppLayout } from "../layouts/AppLayout";
import { DashboardPage } from "../features/dashboard/DashboardPage";
import { MatchWorkbenchPage } from "../features/match-workbench/MatchWorkbenchPage";
import { RuleDesignerPage } from "../features/rule-designer/RuleDesignerPage";
import { PolicyManagerPage } from "../features/policy-manager/PolicyManagerPage";
import { AnalyticsPage } from "../features/analytics/AnalyticsPage";
import { CopilotPage } from "../features/copilot/CopilotPage";
import { AdminConsolePage } from "../features/admin/AdminConsolePage";

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route element={<AppLayout />}>
          <Route path="/" element={<Navigate to="/dashboard" replace />} />
          <Route path="/dashboard" element={<DashboardPage />} />
          <Route path="/matches" element={<MatchWorkbenchPage />} />
          <Route path="/rules" element={<RuleDesignerPage />} />
          <Route path="/policies" element={<PolicyManagerPage />} />
          <Route path="/analytics" element={<AnalyticsPage />} />
          <Route path="/copilot" element={<CopilotPage />} />
          <Route path="/admin" element={<AdminConsolePage />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}
