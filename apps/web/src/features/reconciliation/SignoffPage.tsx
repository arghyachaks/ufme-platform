import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { Alert, Box, Button, LinearProgress, Snackbar, Stack, Table, TableBody, TableCell, TableHead, TableRow, Typography } from "@mui/material";
import CheckCircleRoundedIcon from "@mui/icons-material/CheckCircleRounded";
import RadioButtonUncheckedRoundedIcon from "@mui/icons-material/RadioButtonUncheckedRounded";
import { PageHeader } from "../../components/common/PageHeader";
import { Panel, StatusPill } from "../../components/common/Panel";
import { ActivityTimeline } from "./ActivityTimeline";
import { api, ApiError } from "../../api/services";
import type { SignoffState } from "../../api/types";
import { useQuery } from "../../api/useQuery";
import { PageSkeleton } from "../../components/common/Blocks";

const FLOW = ["Open", "Manager signed", "Controller signed", "Signed off"];
const tone = (s: SignoffState): "ok" | "warn" | "crit" => (s.status === "Signed off" ? "ok" : s.ready ? "warn" : "crit");

export function SignoffPage() {
  const q = useQuery(api.workflow.signoff);
  return q.data ? <SignoffView rows={q.data} reload={q.reload} /> : <PageSkeleton />;
}

function SignoffView({ rows, reload }: { rows: SignoffState[]; reload: () => void }) {
  const navigate = useNavigate();
  const [entity, setEntity] = useState(rows.find((r) => !r.ready)?.entity ?? rows[0]?.entity);
  const [busy, setBusy] = useState(false);
  const [toast, setToast] = useState<{ text: string; error?: boolean } | null>(null);
  const sel = rows.find((r) => r.entity === entity) ?? rows[0];
  const signed = rows.filter((r) => r.status === "Signed off").length;

  async function run(fn: () => Promise<unknown>, ok: string) {
    setBusy(true);
    try {
      await fn();
      setToast({ text: ok });
    } catch (e) {
      setToast({ text: e instanceof ApiError ? e.message : String(e), error: true });
    } finally {
      setBusy(false);
      reload();
    }
  }

  if (!sel) return <PageSkeleton />;
  return (
    <>
      <PageHeader
        title="Period sign-off"
        description="Sign-off unlocks only when the run is complete, approvals are cleared, controls pass and no critical exceptions remain. Each step is signed by a different person and recorded in the audit trail."
        actions={
          <Stack direction="row" spacing={1}>
            <Button variant="outlined" disabled={busy} onClick={() => run(api.workflow.evaluateControls, "Controls re-tested from current data")}>
              Re-test controls
            </Button>
            <Button variant="contained" disabled={busy || !sel.ready || !sel.nextSigner} onClick={() => run(() => api.workflow.sign(sel.entity), `${sel.entity} signed`)}>
              {sel.nextSigner ? `Sign ${sel.entity}` : `${sel.entity} signed off`}
            </Button>
          </Stack>
        }
      />

      <Box sx={{ display: "grid", gridTemplateColumns: { xs: "1fr 1fr", lg: "repeat(4, 1fr)" }, gap: 2 }}>
        {[
          { label: "Entities signed", value: `${signed} / ${rows.length}` },
          { label: `${sel.entity} readiness`, value: `${sel.readiness}%` },
          { label: "Open exceptions", value: String(sel.openExceptions) },
          { label: "Pending approvals", value: String(sel.pendingApprovals) },
        ].map((k) => (
          <Box key={k.label} className="card-enter" sx={{ p: 1.75, borderRadius: "10px", border: "1px solid var(--glass-border)", bgcolor: "var(--bg-surface)" }}>
            <Typography sx={{ fontSize: 10.5, fontFamily: "var(--font-mono)", color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.07em" }}>{k.label}</Typography>
            <Typography className="display" sx={{ fontSize: 26, lineHeight: 1.2 }}>{k.value}</Typography>
          </Box>
        ))}
      </Box>

      <Box sx={{ display: "grid", gridTemplateColumns: { xs: "1fr", xl: "1.4fr 1fr" }, gap: 2.5 }}>
        <Panel title={`Entities · ${rows[0]?.period ?? ""}`}>
          <Table size="small">
            <TableHead>
              <TableRow>
                <TableCell>Entity</TableCell>
                <TableCell>Status</TableCell>
                <TableCell>Readiness</TableCell>
                <TableCell align="right">Open exceptions</TableCell>
                <TableCell align="right">Pending approvals</TableCell>
                <TableCell>Next signer</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {rows.map((r) => (
                <TableRow key={r.entity} hover selected={r.entity === sel.entity} onClick={() => setEntity(r.entity)} sx={{ cursor: "pointer" }}>
                  <TableCell sx={{ fontFamily: "var(--font-mono)" }}>{r.entity}</TableCell>
                  <TableCell><StatusPill label={r.status.toUpperCase()} tone={tone(r)} /></TableCell>
                  <TableCell sx={{ minWidth: 120 }}>
                    <Stack direction="row" alignItems="center" spacing={1}>
                      <LinearProgress variant="determinate" value={r.readiness} sx={{ flex: 1 }} />
                      <Typography sx={{ fontSize: 11.5, fontFamily: "var(--font-mono)" }}>{r.readiness}%</Typography>
                    </Stack>
                  </TableCell>
                  <TableCell align="right">{r.openExceptions}</TableCell>
                  <TableCell align="right">{r.pendingApprovals}</TableCell>
                  <TableCell>{r.nextSigner ?? "—"}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </Panel>

        <Panel title={`${sel.entity} close pack`}>
          <Stack direction="row" spacing={0.75} alignItems="center" flexWrap="wrap" sx={{ mb: 2 }}>
            {FLOW.map((step, i) => {
              const reached = FLOW.indexOf(sel.status) >= i;
              return (
                <Stack key={step} direction="row" alignItems="center" spacing={0.75}>
                  <Box sx={{ px: 1, py: 0.4, borderRadius: "6px", fontSize: 11, fontWeight: 600, bgcolor: reached ? "var(--indigo-soft)" : "var(--bg-muted)", color: reached ? "var(--brand-indigo)" : "text.secondary" }}>
                    {step}
                  </Box>
                  {i < FLOW.length - 1 ? <Typography sx={{ color: "text.secondary" }}>→</Typography> : null}
                </Stack>
              );
            })}
          </Stack>
          <Typography variant="overline">Checklist</Typography>
          <Stack spacing={0.75} sx={{ my: 1 }}>
            {sel.checklist.map((c) => (
              <Stack key={c.label} direction="row" spacing={1} alignItems="center">
                {c.done ? <CheckCircleRoundedIcon sx={{ fontSize: 18, color: "var(--brand-emerald)" }} /> : <RadioButtonUncheckedRoundedIcon sx={{ fontSize: 18, color: "text.disabled" }} />}
                <Typography sx={{ fontSize: 13 }}>{c.label}</Typography>
              </Stack>
            ))}
          </Stack>
          {sel.blockers.length ? (
            <Alert severity="warning" sx={{ my: 1.5 }}>
              <Typography sx={{ fontSize: 12.5, fontWeight: 600, mb: 0.5 }}>Blocked until:</Typography>
              {sel.blockers.map((b) => (
                <Typography key={b} sx={{ fontSize: 12.5 }}>• {b}</Typography>
              ))}
            </Alert>
          ) : sel.nextSigner ? (
            <Alert severity="success" sx={{ my: 1.5 }}>Ready. The next signature needs a {sel.nextSigner} or above.</Alert>
          ) : null}
          <Stack direction="row" spacing={1} flexWrap="wrap" sx={{ mb: 1.5 }}>
            {sel.pendingApprovals ? <Button size="small" variant="outlined" onClick={() => navigate("/reconciliation/approvals")}>Open approvals</Button> : null}
            {sel.criticalExceptions ? <Button size="small" variant="outlined" onClick={() => navigate("/exceptions")}>Open exceptions</Button> : null}
            {sel.failingControls.length ? <Button size="small" variant="outlined" onClick={() => navigate("/audit")}>View controls</Button> : null}
          </Stack>
          <Typography variant="overline">Signatures</Typography>
          {sel.signatures.length ? (
            sel.signatures.map((s) => (
              <Typography key={s.at} sx={{ fontSize: 12, fontFamily: "var(--font-mono)", color: "text.secondary" }}>
                {s.at.slice(0, 16).replace("T", " ")} · {s.name} ({s.role}) · {s.step}
              </Typography>
            ))
          ) : (
            <Typography sx={{ fontSize: 12.5, color: "text.secondary" }}>No signatures yet this period.</Typography>
          )}
        </Panel>
      </Box>
      <ActivityTimeline />
      <Snackbar open={Boolean(toast)} autoHideDuration={6000} onClose={() => setToast(null)} anchorOrigin={{ vertical: "bottom", horizontal: "center" }}>
        <Alert severity={toast?.error ? "warning" : "success"} variant="filled" onClose={() => setToast(null)} sx={{ maxWidth: 620 }}>
          {toast?.text}
        </Alert>
      </Snackbar>
    </>
  );
}
