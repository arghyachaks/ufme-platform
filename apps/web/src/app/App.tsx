import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import { AppLayout } from "../layouts/AppLayout";
import { DashboardPage } from "../features/dashboard/DashboardPage";
import { EntityRiskPage } from "../features/risk/EntityRiskPage";
import { WorkspacePage } from "../features/workspace/WorkspacePage";

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route element={<AppLayout />}>
          <Route path="/" element={<Navigate to="/dashboard" replace />} />
          <Route path="/dashboard" element={<DashboardPage />} />
          <Route path="/risk/:entityId" element={<EntityRiskPage />} />
          <Route path="/reconciliation/runs" element={<WorkspacePage />} />
          <Route path="/reconciliation/review" element={<WorkspacePage />} />
          <Route path="/reconciliation/manual-match" element={<WorkspacePage />} />
          <Route path="/reconciliation/approvals" element={<WorkspacePage />} />
          <Route path="/reconciliation/signoff" element={<WorkspacePage />} />
          <Route path="/exceptions" element={<WorkspacePage />} />
          <Route path="/exceptions/cases" element={<WorkspacePage />} />
          <Route path="/exceptions/investigations" element={<WorkspacePage />} />
          <Route path="/knowledge-graph" element={<WorkspacePage />} />
          <Route path="/rules" element={<WorkspacePage />} />
          <Route path="/rules/policies" element={<WorkspacePage />} />
          <Route path="/rules/simulation" element={<WorkspacePage />} />
          <Route path="/rules/workflow" element={<WorkspacePage />} />
          <Route path="/ai/copilot" element={<WorkspacePage />} />
          <Route path="/ai/explainability" element={<WorkspacePage />} />
          <Route path="/ai/models" element={<WorkspacePage />} />
          <Route path="/ai/learning" element={<WorkspacePage />} />
          <Route path="/data/sources" element={<WorkspacePage />} />
          <Route path="/data/quality" element={<WorkspacePage />} />
          <Route path="/data/lineage" element={<WorkspacePage />} />
          <Route path="/data/features" element={<WorkspacePage />} />
          <Route path="/audit" element={<WorkspacePage />} />
          <Route path="/administration" element={<WorkspacePage />} />
          <Route path="/platform" element={<WorkspacePage />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}
