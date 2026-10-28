import { useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  Alert,
  Box,
  Button,
  Checkbox,
  LinearProgress,
  Snackbar,
  Stack,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableRow,
  TextField,
  Tooltip,
  Typography,
} from "@mui/material";
import { PageHeader } from "../../components/common/PageHeader";
import { Panel, StatusPill } from "../../components/common/Panel";
import { ActivityTimeline } from "./ActivityTimeline";
import { api, ApiError } from "../../api/services";
import type { Approval } from "../../api/types";
import { useQuery } from "../../api/useQuery";
import { PageSkeleton } from "../../components/common/Blocks";

const materialityTone: Record<string, "ok" | "warn" | "crit"> = { High: "crit", Medium: "warn", Low: "ok" };
const HIERARCHY = ["Manager", "Controller", "Finance Director"];
type Action = "approve" | "reject" | "request-info";
const verb: Record<Action, string> = { approve: "Approved", reject: "Rejected", "request-info": "Requested info on" };

const money = (usd: number) =>
  usd >= 1e6 ? `$${(usd / 1e6).toFixed(1)}M` : usd >= 1e3 ? `$${(usd / 1e3).toFixed(0)}K` : `$${usd.toFixed(0)}`;

export function ApprovalsPage() {
  const q = useQuery(api.workflow.approvals);
  return q.data ? <ApprovalsView rows={q.data} reload={q.reload} /> : <PageSkeleton />;
}

function ApprovalsView({ rows, reload }: { rows: Approval[]; reload: () => void }) {
  const navigate = useNavigate();
  const [selectedId, setSelectedId] = useState(rows[0]?.id);
  const [checked, setChecked] = useState<string[]>([]);
  const [comment, setComment] = useState("");
  const [busy, setBusy] = useState(false);
  const [toast, setToast] = useState<{ text: string; error?: boolean } | null>(null);
  const selected = rows.find((r) => r.id === selectedId) ?? rows[0];
  const allChecked = rows.length > 0 && checked.length === rows.length;

  const kpis = useMemo(
    () => [
      { label: "Pending approval", value: String(rows.length) },
      { label: "High materiality", value: String(rows.filter((r) => r.materiality === "High").length) },
      { label: "SLA breached", value: String(rows.filter((r) => r.slaOverdue).length) },
      { label: "Exposure awaiting", value: money(rows.reduce((s, r) => s + r.exposureUsd, 0)) },
    ],
    [rows],
  );

  async function act(codes: string[], action: Action) {
    if (!codes.length || busy) return;
    setBusy(true);
    const errors: string[] = [];
    let ok = 0;
    for (const code of codes) {
      try {
        await api.workflow.decideApproval(code, action, comment.trim() || undefined);
        ok += 1;
      } catch (e) {
        errors.push(e instanceof ApiError ? e.message : String(e));
      }
    }
    setBusy(false);
    setChecked([]);
    setComment("");
    setToast(
      errors.length
        ? { text: `${ok ? `${verb[action]} ${ok}. ` : ""}${errors[0]}${errors.length > 1 ? ` (+${errors.length - 1} more)` : ""}`, error: true }
        : { text: `${verb[action]} ${ok} ${ok === 1 ? "match" : "matches"}` },
    );
    reload();
  }

  return (
    <>
      <PageHeader
        title="Approvals"
        description="Matches routed by the approval matrix: under 50K to a Manager, up to 1M to a Controller, above 1M to the Finance Director with a second approver. Nobody can approve their own submission."
        actions={
          <Button variant="outlined" onClick={() => navigate("/reconciliation/review")}>
            Back to review
          </Button>
        }
      />
      <Box sx={{ display: "grid", gridTemplateColumns: { xs: "1fr 1fr", lg: "repeat(4, 1fr)" }, gap: 2 }}>
        {kpis.map((kpi) => (
          <Box key={kpi.label} className="card-enter" sx={{ p: 1.75, borderRadius: "10px", border: "1px solid var(--glass-border)", bgcolor: "var(--bg-surface)" }}>
            <Typography sx={{ fontSize: 10.5, fontFamily: "var(--font-mono)", color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.07em" }}>{kpi.label}</Typography>
            <Typography className="display" sx={{ fontSize: 26, lineHeight: 1.2 }}>{kpi.value}</Typography>
          </Box>
        ))}
      </Box>

      {rows.length === 0 ? (
        <Panel title="Queue">
          <Typography sx={{ fontSize: 13, color: "text.secondary" }}>
            Nothing is waiting for approval. Accepting a suggestion in Review, or creating a manual match, sends it here.
          </Typography>
        </Panel>
      ) : (
        <>
          <Stack direction="row" spacing={1} flexWrap="wrap">
            <Button size="small" variant="contained" disabled={!checked.length || busy} onClick={() => act(checked, "approve")}>
              Approve selected
            </Button>
            <Button size="small" variant="outlined" color="error" disabled={!checked.length || busy} onClick={() => act(checked, "reject")}>
              Reject selected
            </Button>
            <Button size="small" variant="outlined" disabled={!checked.length || busy} onClick={() => act(checked, "request-info")}>
              Request info
            </Button>
          </Stack>

          <Box sx={{ display: "grid", gridTemplateColumns: { xs: "1fr", xl: "1.5fr 1fr" }, gap: 2.5 }}>
            <Panel title={`Queue · ${rows.length}`}>
              <Table size="small">
                <TableHead>
                  <TableRow>
                    <TableCell padding="checkbox">
                      <Checkbox
                        size="small"
                        checked={allChecked}
                        indeterminate={checked.length > 0 && !allChecked}
                        onChange={() => setChecked(allChecked ? [] : rows.map((r) => r.id))}
                      />
                    </TableCell>
                    <TableCell>Match</TableCell>
                    <TableCell>Submitted by</TableCell>
                    <TableCell>Entities</TableCell>
                    <TableCell align="right">Exposure</TableCell>
                    <TableCell>Materiality</TableCell>
                    <TableCell>SLA</TableCell>
                    <TableCell>Needs</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {rows.map((row) => (
                    <TableRow key={row.id} hover selected={row.id === selected?.id} onClick={() => setSelectedId(row.id)} sx={{ cursor: "pointer" }}>
                      <TableCell padding="checkbox" onClick={(e) => e.stopPropagation()}>
                        <Checkbox
                          size="small"
                          checked={checked.includes(row.id)}
                          onChange={() => setChecked((c) => (c.includes(row.id) ? c.filter((x) => x !== row.id) : [...c, row.id]))}
                        />
                      </TableCell>
                      <TableCell sx={{ fontFamily: "var(--font-mono)" }}>
                        {row.matchId}
                        <Typography sx={{ fontSize: 10, color: "text.secondary" }}>
                          {row.kind === "manual" ? "Manual match" : "From review"}
                          {row.status === "Info requested" ? " · info requested" : ""}
                        </Typography>
                      </TableCell>
                      <TableCell>{row.submittedBy}</TableCell>
                      <TableCell>{row.entity}</TableCell>
                      <TableCell align="right" sx={{ fontFamily: "var(--font-mono)" }}>{row.exposure}</TableCell>
                      <TableCell><StatusPill label={row.materiality.toUpperCase()} tone={materialityTone[row.materiality]} /></TableCell>
                      <TableCell><StatusPill label={row.sla} tone={row.slaOverdue ? "crit" : "warn"} /></TableCell>
                      <TableCell>
                        {row.stage}
                        {row.approvalsNeeded > 1 ? ` ×${row.approvalsNeeded}` : ""}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </Panel>

            {selected ? (
              <Panel title={selected.matchId} action={<Typography sx={{ fontSize: 11, color: "text.secondary", fontFamily: "var(--font-mono)" }}>{selected.id}</Typography>}>
                <Typography sx={{ fontSize: 12, color: "text.secondary", mb: 1.5 }}>
                  {selected.entity} · {selected.exposure} · confidence {selected.confidence}
                </Typography>
                <Typography variant="overline">Approval path</Typography>
                <Stack direction="row" spacing={0.75} alignItems="center" flexWrap="wrap" sx={{ mb: 1.5, mt: 0.5 }}>
                  {HIERARCHY.map((role, i) => (
                    <Stack key={role} direction="row" alignItems="center" spacing={0.75}>
                      <Box
                        sx={{
                          px: 1, py: 0.4, borderRadius: "6px", fontSize: 11, fontWeight: 600,
                          bgcolor: role === selected.stage ? "primary.main" : "var(--bg-muted)",
                          color: role === selected.stage ? "primary.contrastText" : "text.secondary",
                        }}
                      >
                        {role}
                      </Box>
                      {i < HIERARCHY.length - 1 ? <Typography sx={{ color: "text.secondary" }}>→</Typography> : null}
                    </Stack>
                  ))}
                </Stack>
                {selected.approvalsNeeded > 1 ? (
                  <Alert severity="info" sx={{ mb: 1.5 }}>
                    Dual control: {selected.approvals.length} of {selected.approvalsNeeded} approvals from different people.
                  </Alert>
                ) : null}
                <Typography variant="overline">Rationale</Typography>
                <Typography sx={{ fontSize: 12.5, mb: 1.5 }}>{selected.rationale}</Typography>
                {selected.confidenceFactors.length ? (
                  <>
                    <Typography variant="overline">What drove the match</Typography>
                    <Stack spacing={0.6} sx={{ mb: 1.5, mt: 0.5 }}>
                      {selected.confidenceFactors.map((f) => (
                        <Stack key={f.label} spacing={0.25}>
                          <Stack direction="row" justifyContent="space-between">
                            <Typography sx={{ fontSize: 11.5 }}>{f.label}</Typography>
                            <Typography sx={{ fontSize: 11.5, fontFamily: "var(--font-mono)" }}>{f.weight}%</Typography>
                          </Stack>
                          <LinearProgress variant="determinate" value={f.weight} />
                        </Stack>
                      ))}
                    </Stack>
                  </>
                ) : null}
                <Typography variant="overline">Audit trail</Typography>
                <Stack sx={{ mb: 1.5, mt: 0.5 }}>
                  {selected.trail.map((t) => (
                    <Typography key={t} sx={{ fontSize: 12, fontFamily: "var(--font-mono)", color: "text.secondary" }}>{t}</Typography>
                  ))}
                </Stack>
                <TextField size="small" fullWidth placeholder="Comment (optional, saved to the audit trail)" value={comment} onChange={(e) => setComment(e.target.value)} sx={{ mb: 1.5 }} />
                <Stack direction="row" spacing={1} flexWrap="wrap">
                  <Tooltip title="Approve. The server checks your authority and segregation of duties.">
                    <span>
                      <Button variant="contained" disabled={busy} onClick={() => act([selected.id], "approve")}>Approve</Button>
                    </span>
                  </Tooltip>
                  <Button variant="outlined" color="error" disabled={busy} onClick={() => act([selected.id], "reject")}>Reject</Button>
                  <Button variant="outlined" disabled={busy} onClick={() => act([selected.id], "request-info")}>Request information</Button>
                </Stack>
              </Panel>
            ) : null}
          </Box>
        </>
      )}
      <ActivityTimeline />
      <Snackbar open={Boolean(toast)} autoHideDuration={5000} onClose={() => setToast(null)} anchorOrigin={{ vertical: "bottom", horizontal: "center" }}>
        <Alert severity={toast?.error ? "warning" : "success"} variant="filled" onClose={() => setToast(null)} sx={{ maxWidth: 560 }}>
          {toast?.text}
        </Alert>
      </Snackbar>
    </>
  );
}
