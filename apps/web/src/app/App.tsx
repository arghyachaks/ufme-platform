import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import { AppLayout } from "../layouts/AppLayout";
import { DashboardPage } from "../features/dashboard/DashboardPage";
import { EntityRiskPage } from "../features/risk/EntityRiskPage";
import { WorkspacePage } from "../features/workspace/WorkspacePage";
import { ReconLayout } from "../features/reconciliation/ReconLayout";
import { RunsPage } from "../features/reconciliation/RunsPage";
import { ReviewPage } from "../features/reconciliation/ReviewPage";
import { ManualMatchPage } from "../features/reconciliation/ManualMatchPage";
import { ApprovalsPage } from "../features/reconciliation/ApprovalsPage";
import { SignoffPage } from "../features/reconciliation/SignoffPage";

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route element={<AppLayout />}>
          <Route path="/" element={<Navigate to="/dashboard" replace />} />
          <Route path="/dashboard" element={<DashboardPage />} />
          <Route path="/risk/:entityId" element={<EntityRiskPage />} />
          <Route path="/reconciliation" element={<ReconLayout />}>
            <Route index element={<Navigate to="runs" replace />} />
            <Route path="runs" element={<RunsPage />} />
            <Route path="review" element={<ReviewPage />} />
            <Route path="manual-match" element={<ManualMatchPage />} />
            <Route path="approvals" element={<ApprovalsPage />} />
            <Route path="signoff" element={<SignoffPage />} />
          </Route>
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
