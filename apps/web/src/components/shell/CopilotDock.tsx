import { Box, Button, Stack, Typography } from "@mui/material";
import { Link as RouterLink, useLocation, useNavigate } from "react-router-dom";
import { workspaceApi, type DashboardData, type ReconData } from "../../api/services";
import { useQuery } from "../../api/useQuery";
import { AssistChat, AssistStatusChip } from "./AssistChat";

export function CopilotDock() {
  const { data } = useQuery(workspaceApi.dashboard);
  return data ? <CopilotDockView d={data} /> : null;
}

function CopilotDockView({ d }: { d: DashboardData }) {
  const { copilotActions, copilotThread } = d;
  const { pathname } = useLocation();
  const recon = pathname.startsWith("/reconciliation");

  return (
    <Box
      className="ufme-copilot"
      sx={{
        bgcolor: "transparent",
        borderLeft: "1px solid",
        borderColor: "divider",
        display: "flex",
        flexDirection: "column",
        p: 2,
        minHeight: 0,
      }}
    >
      <Stack
        direction="row"
        justifyContent="space-between"
        alignItems="center"
        sx={{ pb: 1.5, borderBottom: "1px solid", borderColor: "divider" }}
      >
        <Typography sx={{ fontSize: 14, fontWeight: 700, color: "primary.main" }}>ufme Assist</Typography>
        <AssistStatusChip />
      </Stack>

      <Box sx={{ py: 1.5, borderBottom: "1px solid", borderColor: "divider" }}>
        {recon ? <ContextualAdvisor pathname={pathname} /> : (
          <>
            <Typography sx={{ fontSize: 11, fontWeight: 700, mb: 0.75 }}>Recommended Actions</Typography>
            <Typography sx={{ fontSize: 11, color: "success.main", fontWeight: 700, mb: 1 }}>
              Estimated benefit: +$210M reduction
            </Typography>
            <Stack spacing={0.75}>
              {copilotActions.map((action) => (
                <Button
                  key={action.label}
                  component={RouterLink}
                  to={action.to}
                  size="small"
                  variant="outlined"
                  sx={{ justifyContent: "flex-start", fontSize: 11 }}
                >
                  {action.label}
                </Button>
              ))}
            </Stack>
          </>
        )}
      </Box>

      <AssistChat
        key={pathname.split("/")[1]}
        page={pathname}
        seed={copilotThread.map((m) => ({ role: m.role === "user" ? "user" : "assistant", text: m.text }))}
        placeholder={
          pathname.includes("manual-match")
            ? "Ask for another combination..."
            : pathname.includes("approvals")
              ? "Ask whether to approve this match..."
              : pathname.includes("signoff")
                ? "Ask if APAC is ready to sign..."
                : recon
                  ? "Ask why this match ranked first..."
                  : "Ask anything, e.g. \"Why is EX-8902 open?\""
        }
      />
    </Box>
  );
}

function ContextualAdvisor({ pathname }: { pathname: string }) {
  const navigate = useNavigate();
  if (pathname.includes("manual-match")) {
    return (
      <Stack spacing={1}>
        <Typography sx={{ fontSize: 11, fontWeight: 700 }}>Suggested combination</Typography>
        <Typography sx={{ fontSize: 16, fontWeight: 800 }}>1:M · SG-4501 → 4501-A + 4501-B</Typography>
        <Typography sx={{ fontSize: 12 }}>Amount similarity 100% after split. Variance 0.00% vs 0.5% policy.</Typography>
        <Button variant="contained" size="small" onClick={() => navigate("/reconciliation/manual-match")}>
          Apply combination
        </Button>
      </Stack>
    );
  }
  if (pathname.includes("approvals")) {
    return (
      <Stack spacing={1}>
        <Typography sx={{ fontSize: 11, fontWeight: 700 }}>Recommended decision</Typography>
        <Typography sx={{ fontSize: 16, fontWeight: 800 }}>Approve MT-9004 · Reject MT-8902</Typography>
        <Typography sx={{ fontSize: 12 }}>MT-9004 is within policy. MT-8902 is High materiality and 2 days overdue.</Typography>
        <Button variant="contained" size="small" onClick={() => navigate("/reconciliation/approvals")}>
          Apply recommendation
        </Button>
      </Stack>
    );
  }
  if (pathname.includes("signoff")) {
    return (
      <Stack spacing={1}>
        <Typography sx={{ fontSize: 11, fontWeight: 700 }}>Readiness decision</Typography>
        <Typography sx={{ fontSize: 16, fontWeight: 800 }}>Hold APAC E09</Typography>
        <Typography sx={{ fontSize: 12 }}>92% ready. 1 control failed and 4 critical exceptions remain.</Typography>
        <Button variant="contained" size="small" onClick={() => navigate("/exceptions")}>
          Review blockers
        </Button>
      </Stack>
    );
  }
  return <MatchAdvisor />;
}

function MatchAdvisor() {
  const { data } = useQuery(workspaceApi.recon);
  return data ? <MatchAdvisorView d={data} /> : null;
}

function MatchAdvisorView({ d }: { d: ReconData }) {
  const { suggestedMatch, advisorMetrics } = d;
  const navigate = useNavigate();
  return (
    <Stack spacing={1}>
      <Typography sx={{ fontSize: 11, fontWeight: 700 }}>Recommended decision</Typography>
      <Typography sx={{ fontSize: 18, fontWeight: 800 }}>{suggestedMatch.decision}</Typography>
      <Typography sx={{ fontSize: 12 }}>
        Confidence <Box component="strong">{suggestedMatch.confidence}</Box>
      </Typography>
      <Typography sx={{ fontSize: 12 }}>Expected exposure reduction {advisorMetrics.exposureReduction}</Typography>
      <Typography sx={{ fontSize: 12 }}>Expected match improvement {advisorMetrics.matchImprovement}</Typography>
      <Typography sx={{ fontSize: 12, color: "success.main", fontWeight: 700 }}>
        Estimated auto-match gain {advisorMetrics.autoMatchGain}
      </Typography>
      <Typography sx={{ fontSize: 11, fontWeight: 700, pt: 0.5 }}>Similar cases</Typography>
      {suggestedMatch.similarCases.map((item) => (
        <Typography key={item} sx={{ fontSize: 11, color: "text.secondary" }}>
          {item}
        </Typography>
      ))}
      <Button variant="contained" size="small" onClick={() => navigate("/reconciliation/review")}>
        One-click apply
      </Button>
    </Stack>
  );
}
