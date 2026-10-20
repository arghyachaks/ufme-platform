import { useState } from "react";
import { NavLink, Outlet, useLocation, useNavigate } from "react-router-dom";
import { CircularProgress, Snackbar } from "@mui/material";
import { api, ApiError } from "../../api/services";
import { Box, Button, MenuItem, Select, Stack, Typography } from "@mui/material";
import { workspaceApi, type ReconData } from "../../api/services";
import { useQuery } from "../../api/useQuery";

const steps = [
  { label: "Runs", to: "/reconciliation/runs" },
  { label: "Review", to: "/reconciliation/review" },
  { label: "Manual Match", to: "/reconciliation/manual-match" },
  { label: "Approvals", to: "/reconciliation/approvals" },
  { label: "Signoff", to: "/reconciliation/signoff" },
];

export function ReconLayout() {
  const { data } = useQuery(workspaceApi.recon);
  return data ? <ReconLayoutView d={data} /> : null;
}

function ReconLayoutView({ d }: { d: ReconData }) {
  const { reconContext } = d;
  const { pathname } = useLocation();
  const navigate = useNavigate();

  return (
    <Stack spacing={3}>
      <Stack
        direction={{ xs: "column", md: "row" }}
        justifyContent="space-between"
        alignItems={{ md: "center" }}
        gap={2}
        sx={{
          p: 2,
          bgcolor: "var(--glass-bg)", backdropFilter: "blur(18px) saturate(150%)",
          border: "1px solid",
          borderColor: "divider",
          borderRadius: 1,
        }}
      >
        <Stack direction="row" spacing={1} flexWrap="wrap">
          <Select size="small" value={reconContext.period} sx={{ minWidth: 120 }}>
            <MenuItem value={reconContext.period}>{reconContext.period}</MenuItem>
          </Select>
          <Select size="small" value={reconContext.entity} sx={{ minWidth: 110 }}>
            <MenuItem value={reconContext.entity}>{reconContext.entity}</MenuItem>
          </Select>
          <Select size="small" value={reconContext.type} sx={{ minWidth: 150 }}>
            <MenuItem value={reconContext.type}>{reconContext.type}</MenuItem>
          </Select>
        </Stack>
        <RunButton onDone={() => navigate("/reconciliation/runs")} />
      </Stack>

      <Stack direction="row" spacing={1} sx={{ overflowX: "auto", pb: 0.5 }}>
        {steps.map((step, index) => {
          const active = pathname === step.to;
          return (
            <Button
              key={step.to}
              component={NavLink}
              to={step.to}
              size="small"
              variant={active ? "contained" : "outlined"}
              sx={{ whiteSpace: "nowrap" }}
            >
              {index + 1}. {step.label}
            </Button>
          );
        })}
      </Stack>

      <Box sx={{ display: "flex", flexDirection: "column", gap: 3 }}>
        <Outlet />
      </Box>
    </Stack>
  );
}

export function ReconRecoBar() {
  const { data } = useQuery(workspaceApi.recon);
  return data ? <ReconRecoBarView d={data} /> : null;
}

function ReconRecoBarView({ d }: { d: ReconData }) {
  const { aiRecoCard } = d;
  const navigate = useNavigate();
  return (
    <Box
      className="card-enter"
      sx={{
        p: 2.25,
        borderRadius: 1,
        bgcolor: "var(--glass-bg)", backdropFilter: "blur(18px) saturate(150%)",
        border: "1px solid",
        borderColor: "primary.main",
        boxShadow: "0 0 0 3px var(--indigo-soft)",
      }}
    >
      <Stack direction={{ xs: "column", md: "row" }} justifyContent="space-between" gap={2} alignItems={{ md: "center" }}>
        <Box>
          <Typography sx={{ fontSize: 11, fontWeight: 700, letterSpacing: "0.06em", textTransform: "uppercase", color: "primary.main" }}>
            Suggested match
          </Typography>
          <Typography sx={{ fontSize: 16, fontWeight: 700, mt: 0.5 }}>{aiRecoCard.title}</Typography>
          <Typography sx={{ fontSize: 12, color: "text.secondary", mt: 0.5 }}>{aiRecoCard.detail}</Typography>
          <Stack direction="row" spacing={2} sx={{ mt: 1 }}>
            <Typography sx={{ fontSize: 12 }}>
              Confidence <Box component="strong" sx={{ fontFamily: 'var(--font-mono)' }}>{aiRecoCard.confidence}</Box>
            </Typography>
            <Typography sx={{ fontSize: 12, color: "success.main", fontWeight: 700 }}>{aiRecoCard.impact}</Typography>
            <Typography sx={{ fontSize: 12 }}>Execution time {aiRecoCard.executionTime}</Typography>
          </Stack>
        </Box>
        <Button variant="contained" onClick={() => navigate("/rules/simulation")}>
          One-click execute
        </Button>
      </Stack>
    </Box>
  );
}

function RunButton({ onDone }: { onDone: () => void }) {
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  const start = async () => {
    setBusy(true);
    try {
      let run = await api.recon.startRun();
      for (let i = 0; i < 300 && (run.status === "Queued" || run.status === "Running"); i++) {
        await new Promise((r) => setTimeout(r, 1000));
        run = await api.recon.run(run.id);
      }
      const m = run.metrics as Record<string, number>;
      setMessage(run.status === "Completed"
        ? `${run.id}: ${m.auto?.toLocaleString()} auto-matched, ${m.suggested?.toLocaleString()} to review, ${m.unmatched?.toLocaleString()} open`
        : `${run.id} ${run.status}${run.error ? ` — ${run.error}` : ""}`);
      onDone();
      setTimeout(() => window.location.reload(), 1800);  // refresh the run list and review queue
    } catch (err) {
      setMessage(err instanceof ApiError ? err.message : "Could not start the run");
    } finally {
      setBusy(false);
    }
  };
  return (
    <>
      <Button variant="contained" onClick={start} disabled={busy} startIcon={busy ? <CircularProgress size={14} color="inherit" /> : undefined}>
        {busy ? "Matching…" : "Run Reconciliation"}
      </Button>
      <Snackbar open={Boolean(message)} autoHideDuration={4000} onClose={() => setMessage("")} message={message} />
    </>
  );
}
