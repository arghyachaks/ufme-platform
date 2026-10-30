import { useState } from "react";
import { Box, Button, Stack, Typography } from "@mui/material";
import { api, ApiError } from "../../api/services";
import { useQuery } from "../../api/useQuery";
import type { LearningStatus, ScorerModelInfo } from "../../api/types";
import { Panel, StatusPill } from "../../components/common/Panel";
import { DataTable, KeyValue, Page, PageSkeleton, StatGrid, mono, useToast } from "../../components/common/Blocks";

const TONE: Record<ScorerModelInfo["status"], "ok" | "warn" | "crit"> = {
  active: "ok",
  candidate: "warn",
  training: "warn",
  retired: "warn",
  rolled_back: "crit",
  rejected: "crit",
  failed: "crit",
};
const LABEL: Record<ScorerModelInfo["status"], string> = {
  active: "In use",
  candidate: "Candidate",
  training: "Training",
  retired: "Retired",
  rolled_back: "Rolled back",
  rejected: "Rejected",
  failed: "Failed",
};
const FEATURE: Record<string, string> = {
  amount_gap_log: "Amount agreement",
  amount_gap_usd_log: "Amount difference",
  amount_usd_log: "Item size",
  date_gap_days: "Date difference",
  ref_similarity: "Reference similarity",
  ref_missing: "Missing references",
  ambiguity: "Look-alike items",
  desc_similarity: "Description similarity",
  score: "Model confidence",
};
const pct = (n: number | null | undefined, d = 1) => (n == null ? "—" : `${(100 * n).toFixed(d)}%`);
const when = (iso: string | null) => (iso ? new Date(iso).toLocaleDateString(undefined, { day: "2-digit", month: "short" }) : "—");
const driftTone = (s: string) => (s === "ok" ? "ok" : s === "watch" ? "warn" : s === "alert" ? "crit" : "warn");

export function ModelsPage() {
  const q = useQuery(api.learning.status);
  return (
    <Page
      title="Models"
      description="The model that scores matches for your ledgers: which version is in use, the evidence behind each candidate, and whether today's data still looks like what it was trained on."
      loading={q.loading && !q.data}
    >
      {q.data ? <ModelsView s={q.data} reload={q.reload} /> : <PageSkeleton />}
    </Page>
  );
}

function ModelsView({ s, reload }: { s: LearningStatus; reload: () => void }) {
  const { toast, toastNode } = useToast();
  const [open, setOpen] = useState<string | null>(s.models.find((m) => m.status === "candidate")?.version ?? null);
  const [busy, setBusy] = useState(false);
  const selected = s.models.find((m) => m.version === open) ?? null;
  const drift = s.drift.features;

  const act = async (fn: () => Promise<unknown>, ok: string) => {
    setBusy(true);
    try {
      await fn();
      toast(ok);
      reload();
    } catch (e) {
      toast(e instanceof ApiError ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  };

  return (
    <>
      <StatGrid
        items={[
          { label: "In use", value: s.active, hint: s.activeIsShipped ? "Shipped scorer" : "Tenant model", tone: "ok" },
          { label: "Candidates", value: String(s.models.filter((m) => m.status === "candidate").length) },
          {
            label: "Input drift",
            value: drift?.max_psi != null ? drift.max_psi.toFixed(2) : "—",
            hint: drift?.status === "unknown" || !drift ? "No run yet" : `${drift.status} · PSI alert at 0.25`,
            tone: drift ? (driftTone(drift.status) as "ok" | "warn" | "crit") : undefined,
          },
          { label: "Decisions to learn from", value: s.labels.usable.toLocaleString() },
        ]}
      />
      <Box sx={{ display: "grid", gridTemplateColumns: { xs: "1fr", lg: "1.5fr 1fr" }, gap: 2.5, alignItems: "start" }}>
        <Stack spacing={2.5} sx={{ minWidth: 0 }}>
          <DataTable<ScorerModelInfo>
            rows={s.models}
            rowKey={(m) => m.version}
            selectedKey={open ?? undefined}
            onRowClick={(m) => setOpen(m.version)}
            empty="No tenant models yet. The shipped scorer is in use; train one from Continuous learning."
            columns={[
              { key: "v", header: "Version", render: (m) => <span style={mono}>{m.version}</span> },
              { key: "s", header: "Status", render: (m) => <StatusPill label={LABEL[m.status]} tone={TONE[m.status]} /> },
              { key: "l", header: "Decisions", align: "right", render: (m) => m.labels.toLocaleString() },
              {
                key: "g",
                header: "Gate",
                render: (m) =>
                  m.gate.passed === undefined ? "—" : <StatusPill label={m.gate.passed ? "Passed" : "Blocked"} tone={m.gate.passed ? "ok" : "crit"} />,
              },
              { key: "t", header: "Trained", render: (m) => `${when(m.trainedAt)} · ${m.trainedBy.split("@")[0]}` },
              { key: "p", header: "Promoted", render: (m) => (m.promotedBy ? `${when(m.promotedAt)} · ${m.promotedBy.split("@")[0]}` : "—") },
            ]}
          />
          <Panel title="Input drift (latest run)">
            {!drift || drift.status === "unknown" ? (
              <Typography sx={{ fontSize: 12, color: "text.secondary" }}>
                {drift?.reason ? `Not measured: ${drift.reason}.` : "Run a reconciliation to measure drift."}
              </Typography>
            ) : (
              <>
                <Typography sx={{ fontSize: 12, color: "text.secondary", mb: 1 }}>
                  {s.drift.run}: {drift.pairs?.toLocaleString()} scored pairs compared with what the model was calibrated on.
                  Below 0.10 is stable; 0.25 or more means retrain and re-check.
                </Typography>
                {Object.entries(drift.top ?? {}).map(([k, v]) => (
                  <KeyValue
                    key={k}
                    label={FEATURE[k] ?? k.replace(/_/g, " ")}
                    value={<span style={{ ...mono, color: v >= 0.25 ? "var(--mui-palette-error-main)" : undefined }}>{v.toFixed(3)}</span>}
                  />
                ))}
              </>
            )}
          </Panel>
        </Stack>
        <Stack spacing={2.5}>
          {selected ? (
            <Evidence m={selected} busy={busy}
              onPromote={() => act(() => api.learning.promote(selected.version), `${selected.version} is now in use`)} />
          ) : (
            <Panel title="Evidence">
              <Typography sx={{ fontSize: 12, color: "text.secondary" }}>Select a model to see why it can or can't be promoted.</Typography>
            </Panel>
          )}
          {!s.activeIsShipped ? (
            <Panel title="Roll back">
              <Typography sx={{ fontSize: 12, color: "text.secondary", mb: 1.5 }}>
                Return to the previously promoted model (or the shipped scorer). Takes effect on the next run and is
                recorded in the audit trail.
              </Typography>
              <Button size="small" color="error" variant="outlined" disabled={busy}
                onClick={() => act(api.learning.rollback, "Rolled back. The next run uses the previous model.")}>
                Roll back {s.active}
              </Button>
            </Panel>
          ) : null}
        </Stack>
      </Box>
      {toastNode}
    </>
  );
}

function Evidence({ m, busy, onPromote }: { m: ScorerModelInfo; busy: boolean; onPromote: () => void }) {
  const h = m.gate.holdout;
  const shadow = m.gate.shadow;
  return (
    <Panel title={`Evidence · ${m.version}`}>
      {m.error ? <Typography sx={{ fontSize: 12, color: "error.main", mb: 1 }}>{m.error}</Typography> : null}
      {m.status === "training" ? <Typography sx={{ fontSize: 12, color: "text.secondary" }}>Training in the background…</Typography> : null}
      {(m.gate.checks ?? []).map((c) => (
        <Stack key={c.name} direction="row" spacing={1} alignItems="flex-start" sx={{ py: 0.6, borderBottom: "1px dashed", borderColor: "divider" }}>
          <StatusPill label={c.ok ? "Pass" : "Fail"} tone={c.ok ? "ok" : "crit"} />
          <Box sx={{ minWidth: 0 }}>
            <Typography sx={{ fontSize: 12, fontWeight: 600 }}>{c.name}</Typography>
            <Typography sx={{ fontSize: 11, color: "text.secondary", overflowWrap: "anywhere" }}>{c.detail}</Typography>
          </Box>
        </Stack>
      ))}
      {h ? (
        <Box sx={{ mt: 1.5 }}>
          <KeyValue label="Held-out decisions" value={h.candidate.labels} />
          <KeyValue label="Would auto-match correctly" value={`${h.candidate.would_auto_correct ?? 0} (now ${h.active?.would_auto_correct ?? 0})`} />
          <KeyValue label="Would auto-match wrongly" value={h.candidate.would_auto_wrong ?? 0} />
        </Box>
      ) : null}
      {shadow?.suggestions ? (
        <KeyValue label={`Shadow on ${shadow.run}`} value={`${shadow.would_auto_match} of ${shadow.suggestions} open suggestions would auto-match (now ${shadow.would_auto_match_active})`} />
      ) : null}
      {Object.entries(m.gate.golden ?? {}).map(([name, g]) => (
        <KeyValue key={name} label={`Benchmark ${name}: auto rate`} value={`${pct(g.before.auto_rate)} → ${pct(g.after.auto_rate)} at ${pct(g.after.precision, 0)} precision`} />
      ))}
      {m.autoThreshold != null ? <KeyValue label="Auto-match threshold" value={pct(m.autoThreshold, 2)} /> : null}
      {m.status === "candidate" ? (
        <Box sx={{ mt: 1.5 }}>
          <Button size="small" variant="contained" disabled={busy || !m.gate.passed} onClick={onPromote}>
            Promote to production
          </Button>
          <Typography sx={{ fontSize: 11, color: "text.secondary", mt: 1 }}>
            Needs a Controller or above, and not the person who requested the training.
          </Typography>
        </Box>
      ) : null}
    </Panel>
  );
}
