import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import { AppLayout } from "../layouts/AppLayout";
import { DashboardPage } from "../features/dashboard/DashboardPage";
import { EntityRiskPage } from "../features/risk/EntityRiskPage";
import { ReconLayout } from "../features/reconciliation/ReconLayout";
import { RunsPage } from "../features/reconciliation/RunsPage";
import { ReviewPage } from "../features/reconciliation/ReviewPage";
import { ManualMatchPage } from "../features/reconciliation/ManualMatchPage";
import { ApprovalsPage } from "../features/reconciliation/ApprovalsPage";
import { SignoffPage } from "../features/reconciliation/SignoffPage";
import { ExceptionsDashboardPage } from "../features/exceptions/ExceptionsDashboardPage";
import { InvestigationsPage } from "../features/exceptions/InvestigationsPage";
import { CasesPage } from "../features/cases/CasesPage";
import { RulesPage } from "../features/rules/RulesPage";
import { PoliciesPage } from "../features/rules/PoliciesPage";
import { SimulationPage } from "../features/rules/SimulationPage";
import { WorkflowPage } from "../features/rules/WorkflowPage";
import { CopilotPage } from "../features/ai/CopilotPage";
import { ExplainabilityPage } from "../features/ai/ExplainabilityPage";
import { ModelsPage } from "../features/ai/ModelsPage";
import { AgentOpsPage } from "../features/ai/AgentOpsPage";
import { LearningPage } from "../features/ai/LearningPage";
import { SourcesPage } from "../features/data/SourcesPage";
import { QualityPage } from "../features/data/QualityPage";
import { LineagePage } from "../features/data/LineagePage";
import { FeaturesPage } from "../features/data/FeaturesPage";
import { AuditPage } from "../features/audit/AuditPage";
import { AdministrationPage } from "../features/platform/AdministrationPage";
import { OperationsPage } from "../features/platform/OperationsPage";
import { KnowledgeGraphPage } from "../features/graph/KnowledgeGraphPage";

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
          <Route path="/exceptions" element={<ExceptionsDashboardPage />} />
          <Route path="/exceptions/cases" element={<CasesPage />} />
          <Route path="/exceptions/investigations" element={<InvestigationsPage />} />
          <Route path="/knowledge-graph" element={<KnowledgeGraphPage />} />
          <Route path="/rules" element={<RulesPage />} />
          <Route path="/rules/policies" element={<PoliciesPage />} />
          <Route path="/rules/simulation" element={<SimulationPage />} />
          <Route path="/rules/workflow" element={<WorkflowPage />} />
          <Route path="/ai/copilot" element={<CopilotPage />} />
          <Route path="/ai/explainability" element={<ExplainabilityPage />} />
          <Route path="/ai/models" element={<ModelsPage />} />
          <Route path="/ai/agents" element={<AgentOpsPage />} />
          <Route path="/ai/learning" element={<LearningPage />} />
          <Route path="/data/sources" element={<SourcesPage />} />
          <Route path="/data/quality" element={<QualityPage />} />
          <Route path="/data/lineage" element={<LineagePage />} />
          <Route path="/data/features" element={<FeaturesPage />} />
          <Route path="/audit" element={<AuditPage />} />
          <Route path="/administration" element={<AdministrationPage />} />
          <Route path="/platform" element={<OperationsPage />} />
          <Route path="*" element={<Navigate to="/dashboard" replace />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}
