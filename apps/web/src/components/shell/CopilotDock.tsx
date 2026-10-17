import { Box, Button, InputBase, Stack, Typography } from "@mui/material";
import { Link as RouterLink, useLocation, useNavigate } from "react-router-dom";
import { workspaceApi, type DashboardData, type ReconData } from "../../api/services";
import { useQuery } from "../../api/useQuery";

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
        <Typography sx={{ fontSize: 14, fontWeight: 700, color: "primary.main" }}>AI Match Advisor</Typography>
        <Box
          sx={{
            fontSize: 10,
            fontWeight: 700,
            px: 1,
            py: 0.35,
            borderRadius: 10,
            bgcolor: "var(--emerald-soft)",
            color: "success.main",
            border: "1px solid rgba(5,150,105,0.3)",
          }}
        >
          GPT-4 Financial Tuned
        </Box>
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

      <Stack spacing={1.5} sx={{ flex: 1, overflow: "auto", py: 1.75 }}>
        {copilotThread.map((message, index) => (
          <Box
            key={index}
            sx={{
              p: 1.5,
              borderRadius: 1,
              fontSize: 12,
              lineHeight: 1.5,
              maxWidth: "92%",
              alignSelf: message.role === "user" ? "flex-end" : "flex-start",
              bgcolor: message.role === "user" ? "var(--bg-muted)" : "var(--indigo-soft)",
              color: "text.primary",
            }}
          >
            {message.text}
          </Box>
        ))}
      </Stack>

      <Box sx={{ pt: 1.5, borderTop: "1px solid", borderColor: "divider" }}>
        <InputBase
          fullWidth
          placeholder={
            pathname.includes("manual-match")
              ? "Ask for another combination..."
              : pathname.includes("approvals")
                ? "Ask whether to approve this match..."
                : pathname.includes("signoff")
                  ? "Ask if APAC is ready to sign..."
                  : recon
                    ? "Ask why this match ranked first..."
                    : "Ask Copilot or command agents (e.g. 'Explain EX-8902')..."
          }
          sx={{
            fontSize: 12,
            px: 1.5,
            py: 1,
            bgcolor: "var(--bg-muted)",
            border: "1px solid",
            borderColor: "divider",
            borderRadius: 1,
          }}
        />
      </Box>
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
