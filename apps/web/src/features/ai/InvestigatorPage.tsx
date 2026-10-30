import { useState } from "react";
import { Box, Button, MenuItem, Select, Stack, TextField, Typography } from "@mui/material";
import { api, ApiError } from "../../api/services";
import { useQuery } from "../../api/useQuery";
import type { AgentEvent, InvestigatorRun } from "../../api/types";
import { Panel, StatusPill } from "../../components/common/Panel";
import { DataTable, Page, mono, money, useToast } from "../../components/common/Blocks";
import { AgentWork, answerText, applyEvent, emptyWork, type Work } from "../../components/shell/AgentWork";

const when = (iso: string) => new Date(iso).toLocaleString(undefined, { day: "2-digit", month: "short", hour: "2-digit", minute: "2-digit" });
const TONE = { completed: "ok", awaiting_approval: "warn", running: "warn", failed: "crit", fallback: "warn", cancelled: "warn" } as const;
const LABEL: Record<string, string> = { awaiting_approval: "Waiting for you", completed: "Completed", running: "Running", failed: "Failed", cancelled: "Stopped", fallback: "Fallback" };

export function InvestigatorPage() {
  const pairs = useQuery(api.agents.pairs);
  const runs = useQuery(api.agents.investigations);
  const { toast, toastNode } = useToast();
  const [pair, setPair] = useState("");
  const [question, setQuestion] = useState("");
  const [work, setWork] = useState<Work | null>(null);
  const [busy, setBusy] = useState(false);
  const [runId, setRunId] = useState<string | null>(null);
  const [rationale, setRationale] = useState<string | null>(null);
  const [comment, setComment] = useState("");

  const onEvent = (e: AgentEvent) => {
    if (e.type === "run" || e.type === "paused") setRunId(e.type === "run" ? e.id : e.run);
    setWork((w) => applyEvent(w ?? emptyWork(), e));
  };
  const go = async (fn: () => Promise<void>) => {
    setBusy(true);
    try {
      await fn();
    } catch (e) {
      toast(e instanceof ApiError ? e.message : "The investigator couldn't run.");
    } finally {
      setBusy(false);
      setRationale(null);
      runs.reload();
    }
  };
  const start = () => {
    const p = pair || pairs.data?.[0]?.pair;
    if (!p) return;
    setWork(emptyWork());
    void go(() => api.agents.investigate(p, question || undefined, onEvent));
  };
  const decide = (decision: "approve" | "edit" | "reject") => {
    if (!runId) return;
    const args = decision === "edit" && rationale != null ? { rationale } : undefined;
    void go(() => api.agents.decide(runId, decision, onEvent, { args, comment: comment || undefined }));
    setComment("");
  };
  const open = async (r: InvestigatorRun) => {
    try {
      const d = await api.agents.run(r.id);
      setRunId(r.id);
      setWork(d.events.reduce(applyEvent, emptyWork()));
    } catch (e) {
      toast(e instanceof ApiError ? e.message : "Couldn't open that run.");
    }
  };

  const pending = work?.pending;
  const items = (pending?.args.item_ids as string[] | undefined) ?? [];
  return (
    <Page
      title="Recon Investigator"
      description="An agent that works through one entity pair's unmatched items and proposes matches. It shows its plan and every step; nothing changes until you approve a proposal, and approved proposals still go through the normal approval matrix."
    >
      <Box sx={{ display: "grid", gridTemplateColumns: { xs: "1fr", lg: "3fr 2fr" }, gap: 2, alignItems: "start" }}>
        <Stack spacing={2}>
          <Panel title="Start an investigation">
            <Stack direction={{ xs: "column", sm: "row" }} spacing={1.5} alignItems={{ sm: "center" }}>
              <Select size="small" displayEmpty value={pair} onChange={(e) => setPair(String(e.target.value))} sx={{ minWidth: 260 }}>
                <MenuItem value=""><em>Largest open pair{pairs.data?.[0] ? ` (${pairs.data[0].pair})` : ""}</em></MenuItem>
                {(pairs.data ?? []).map((p) => (
                  <MenuItem key={p.pair} value={p.pair}>{p.pair} · {p.open} open · {money(p.exposureUsd)}</MenuItem>
                ))}
              </Select>
              <TextField size="small" fullWidth placeholder="Optional focus, e.g. 'only the royalty invoices'" value={question} onChange={(e) => setQuestion(e.target.value)} />
              <Button variant="contained" disabled={busy || !(pair || pairs.data?.length)} onClick={start}>{busy ? "Working…" : "Investigate"}</Button>
            </Stack>
          </Panel>

          {work && (
            <Panel title="Investigation">
              <AgentWork w={work} />
              {pending && (
                <Box sx={{ border: "1px solid var(--text-primary)", p: 1.5, mt: 1, bgcolor: "var(--amber-soft)" }}>
                  <Typography sx={{ fontSize: 14, fontWeight: 600, mb: 0.75 }}>The agent proposes a match. Your decision:</Typography>
                  <Typography sx={{ ...mono, fontSize: 13 }}>{items.join("  +  ")}</Typography>
                  <TextField
                    size="small" fullWidth multiline label="Rationale" sx={{ my: 1.25, bgcolor: "var(--bg-surface)" }}
                    value={rationale ?? String(pending.args.rationale ?? "")}
                    onChange={(e) => setRationale(e.target.value)}
                  />
                  <TextField size="small" fullWidth label="Comment (optional)" value={comment} onChange={(e) => setComment(e.target.value)} sx={{ mb: 1.25, bgcolor: "var(--bg-surface)" }} />
                  <Stack direction="row" spacing={1}>
                    <Button variant="contained" disabled={busy} onClick={() => decide(rationale != null ? "edit" : "approve")}>
                      {rationale != null ? "Approve with my rationale" : "Approve and submit"}
                    </Button>
                    <Button color="error" variant="outlined" disabled={busy} onClick={() => decide("reject")}>Reject</Button>
                  </Stack>
                  <Typography sx={{ fontSize: 12, color: "text.secondary", mt: 1 }}>
                    Approving submits a manual match for these items. It then needs the approver your approval matrix requires (by exposure, with dual control above 1M).
                  </Typography>
                </Box>
              )}
              {answerText(work) && (
                <Typography sx={{ fontSize: 14, whiteSpace: "pre-wrap", mt: 1.5 }}>{answerText(work)}</Typography>
              )}
            </Panel>
          )}
        </Stack>

        <Panel title="Recent investigations">
          <DataTable<InvestigatorRun>
            rows={runs.data ?? []}
            rowKey={(r) => r.id}
            onRowClick={(r) => void open(r)}
            empty="No investigations yet."
            columns={[
              { key: "w", header: "When", render: (r) => when(r.startedAt) },
              { key: "p", header: "Pair", render: (r) => <span style={mono}>{r.pair}</span> },
              { key: "u", header: "By", render: (r) => r.actor.split("@")[0] },
              { key: "s", header: "Status", render: (r) => <StatusPill label={LABEL[r.status] ?? r.status} tone={TONE[r.status] ?? "warn"} /> },
            ]}
          />
        </Panel>
      </Box>
      {toastNode}
    </Page>
  );
}
