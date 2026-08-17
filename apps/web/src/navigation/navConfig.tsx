import type { SvgIconComponent } from "@mui/icons-material";
import AccountTreeOutlinedIcon from "@mui/icons-material/AccountTreeOutlined";
import AdminPanelSettingsOutlinedIcon from "@mui/icons-material/AdminPanelSettingsOutlined";
import AssignmentOutlinedIcon from "@mui/icons-material/AssignmentOutlined";
import AutoAwesomeOutlinedIcon from "@mui/icons-material/AutoAwesomeOutlined";
import DashboardOutlinedIcon from "@mui/icons-material/DashboardOutlined";
import FactCheckOutlinedIcon from "@mui/icons-material/FactCheckOutlined";
import GavelOutlinedIcon from "@mui/icons-material/GavelOutlined";
import HubOutlinedIcon from "@mui/icons-material/HubOutlined";
import MonitorHeartOutlinedIcon from "@mui/icons-material/MonitorHeartOutlined";
import ReportProblemOutlinedIcon from "@mui/icons-material/ReportProblemOutlined";
import StorageOutlinedIcon from "@mui/icons-material/StorageOutlined";

export type NavLeaf = {
  label: string;
  to: string;
  description: string;
};

export type NavItem = {
  label: string;
  to?: string;
  icon: SvgIconComponent;
  description: string;
  badge?: number;
  children?: NavLeaf[];
};

export const navItems: NavItem[] = [
  {
    label: "Dashboard",
    to: "/dashboard",
    icon: DashboardOutlinedIcon,
    description: "Command center for match quality, queues, and operational risk.",
  },
  {
    label: "Reconciliation",
    icon: AccountTreeOutlinedIcon,
    description: "Execute, review, match, approve, and sign off reconciliations.",
    children: [
      {
        label: "Runs",
        to: "/reconciliation/runs",
        description: "Track reconciliation executions, coverage, and processing time.",
      },
      {
        label: "Review",
        to: "/reconciliation/review",
        description: "Human-in-the-loop review of suggested 1:1, 1:M, M:1, and M:M matches.",
      },
      {
        label: "Manual Match",
        to: "/reconciliation/manual-match",
        description: "Create or override matches when rules and AI cannot auto-match.",
      },
      {
        label: "Approvals",
        to: "/reconciliation/approvals",
        description: "Controller approvals for overrides, high-risk matches, and policy exceptions.",
      },
      {
        label: "Signoff",
        to: "/reconciliation/signoff",
        description: "Period close sign-off with evidence and residual exception summary.",
      },
    ],
  },
  {
    label: "Exceptions",
    icon: ReportProblemOutlinedIcon,
    badge: 412,
    description: "Case management for unmatched items, SLAs, and investigations.",
    children: [
      {
        label: "Dashboard",
        to: "/exceptions",
        description: "Exception volume, aging, SLA risk, and assignment load.",
      },
      {
        label: "Investigations",
        to: "/exceptions/investigations",
        description: "Deep-dive unmatched items with lineage, features, and evidence.",
      },
    ],
  },
  {
    label: "Cases",
    to: "/exceptions/cases",
    icon: AssignmentOutlinedIcon,
    description: "Assigned cases, comments, escalations, and resolutions.",
  },
  {
    label: "Rules & Policies",
    icon: GavelOutlinedIcon,
    description: "Deterministic matching rules, tolerances, and workflow policy versions.",
    children: [
      {
        label: "Rules",
        to: "/rules",
        description: "Exact, tolerance, and fuzzy matching rules for candidate generation.",
      },
      {
        label: "Policies",
        to: "/rules/policies",
        description: "Published policy versions, SoD, and tolerance thresholds.",
      },
      {
        label: "Simulation",
        to: "/rules/simulation",
        description: "Replay rules against historical or synthetic datasets before publish.",
      },
      {
        label: "Workflow",
        to: "/rules/workflow",
        description: "Review, approval, escalation, and sign-off workflow configuration.",
      },
    ],
  },
  {
    label: "AI Control Hub",
    icon: AutoAwesomeOutlinedIcon,
    description: "Ranking, explainability, model ops, and continuous learning.",
    children: [
      {
        label: "Copilot",
        to: "/ai/copilot",
        description: "Assist analysts with match suggestions, questions, and case summaries.",
      },
      {
        label: "Explainability",
        to: "/ai/explainability",
        description: "Why a match was proposed, with features, rules, and confidence.",
      },
      {
        label: "Models",
        to: "/ai/models",
        description: "Ranking model versions, precision/recall, drift, and deployment.",
      },
      {
        label: "Learning",
        to: "/ai/learning",
        description: "Capture accept/reject outcomes for active learning loops.",
      },
    ],
  },
  {
    label: "Knowledge Graph",
    to: "/knowledge-graph",
    icon: HubOutlinedIcon,
    description: "Entity relationships, vendor graphs, and match evidence links.",
  },
  {
    label: "Data Engine",
    icon: StorageOutlinedIcon,
    description: "Ingestion, quality, lineage, and the augmented feature store.",
    children: [
      {
        label: "Sources",
        to: "/data/sources",
        description: "ERP connectors, files, and APIs feeding the matching engine.",
      },
      {
        label: "Quality",
        to: "/data/quality",
        description: "Validation, normalization, and data quality issues before matching.",
      },
      {
        label: "Lineage",
        to: "/data/lineage",
        description: "Trace a transaction from source through enrichment to a match decision.",
      },
      {
        label: "Features",
        to: "/data/features",
        description: "Versioned feature store used by rules, optimization, and ranking.",
      },
    ],
  },
  {
    label: "Audit & SOX",
    to: "/audit",
    icon: FactCheckOutlinedIcon,
    description: "Search reconciliations, review evidence, and export audit packages.",
  },
  {
    label: "Administration",
    to: "/administration",
    icon: AdminPanelSettingsOutlinedIcon,
    description: "Tenants, identity, legal entities, RBAC, and security configuration.",
  },
  {
    label: "Operations",
    to: "/platform",
    icon: MonitorHeartOutlinedIcon,
    description: "Health, scaling, jobs, backups, and observability for operators.",
  },
];

export function findNavLeaf(pathname: string): NavLeaf | undefined {
  for (const item of navItems) {
    if (item.to === pathname) {
      return { label: item.label, to: item.to, description: item.description };
    }
    const child = item.children?.find((leaf) => leaf.to === pathname);
    if (child) {
      return child;
    }
  }
  return undefined;
}
