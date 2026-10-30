import { useState } from "react";
import { Box, Button, LinearProgress, Stack, Typography } from "@mui/material";
import { api, ApiError } from "../../api/services";
import { useQuery } from "../../api/useQuery";
import type { LearningDecision, LearningStatus, MatchProposal } from "../../api/types";
import { Panel, StatusPill } from "../../components/common/Panel";
import { DataTable, KeyValue, Page, PageSkeleton, StatGrid, mono, useToast } from "../../components/common/Blocks";

const SOURCE: Record<string, string> = {
  review_accept: "Review: accepted",
  review_reject: "Review: rejected",
  approved: "Approval: approved",
  approval_reject: "Approval: rejected",
  legacy: "Earlier decision",
};

const usd = (n: number) =>
  n >= 1e6 ? `$${(n / 1e6).toFixed(1)}M` : n >= 1e3 ? `$${(n / 1e3).toFixed(0)}K` : `$${n.toFixed(0)}`;
const when = (iso: string | null) =>
  iso ? new Date(iso).toLocaleString(undefined, { day: "2-digit", month: "short", hour: "2-digit", minute: "2-digit" }) : "—";

export function LearningPage() {
  const status = useQuery(api.learning.status);
  const queue = useQuery(() => api.recon.proposals({ status: "proposed", order: "learning", limit: "12" }));
  const reload = () => {
    status.reload();
    queue.reload();
  };
  return (
    <Page
      title="Continuous learning"
      description="Every review and approval decision is kept as a labelled example. When there are enough, ufme trains a tenant model, proves it is safe, and waits for a Controller to promote it."
      loading={status.loading && !status.data}
    >
      {status.data ? <LearningView s={status.data} queue={queue.data ?? []} reload={reload} /> : <PageSkeleton />}
    </Page>
  );
}

function LearningView({ s, queue, reload }: { s: LearningStatus; queue: MatchProposal[]; reload: () => void }) {
  const { toast, toastNode } = useToast();
  const [busy, setBusy] = useState<string | null>(null);
  const training = s.models.some((m) => m.status === "training");
  const progress = Math.min(100, Math.round((100 * s.labels.usable) / Math.max(s.labels.minimum, 1)));

  const act = async (key: string, fn: () => Promise<unknown>, ok: string) => {
    setBusy(key);
    try {
      await fn();
      toast(ok);
      reload();
    } catch (e) {
      toast(e instanceof ApiError ? e.message : String(e));
    } finally {
      setBusy(null);
    }
  };

  const outcomes = s.drift.outcomes;
  return (
    <>
      <StatGrid
        items={[
          { label: "Decisions learned from", value: s.labels.usable.toLocaleString(), hint: `${s.labels.total.toLocaleString()} recorded` },
          { label: "Accepted / rejected", value: `${s.labels.accepted} / ${s.labels.rejected}` },
          { label: "New since current model", value: s.labels.sinceActive.toLocaleString() },
          {
            label: "Model in use",
            value: s.active,
            hint: s.activeIsShipped ? "Shipped scorer" : "Tenant model",
            tone: s.activeIsShipped ? undefined : "ok",
          },
        ]}
      />
      <Box sx={{ display: "grid", gridTemplateColumns: { xs: "1fr", lg: "1.6fr 1fr" }, gap: 2.5, alignItems: "start" }}>
        <Stack spacing={2.5} sx={{ minWidth: 0 }}>
          <Panel title="Teach the model">
            <Typography sx={{ fontSize: 12, color: "text.secondary", mb: 1.5 }}>
              A fresh random sample of open suggestions. A representative mix teaches the model more than only borderline cases (we measured it). Accepting sends the
              match for approval as usual.
            </Typography>
            <DataTable<MatchProposal>
              rows={queue}
              rowKey={(p) => p.id}
              empty="No open suggestions. Run a reconciliation to fill the queue."
              columns={[
                { key: "id", header: "Match", render: (p) => <span style={mono}>{p.id}</span> },
                { key: "pair", header: "Pair", render: (p) => p.entityPair },
                { key: "x", header: "Exposure", align: "right", render: (p) => <span style={mono}>{usd(p.exposureUsd)}</span> },
                { key: "c", header: "Confidence", align: "right", render: (p) => <span style={mono}>{(100 * p.confidence).toFixed(0)}%</span> },
                {
                  key: "a",
                  header: "",
                  align: "right",
                  render: (p) => (
                    <Stack direction="row" spacing={0.5} justifyContent="flex-end">
                      <Button size="small" disabled={busy !== null} onClick={() => act(p.id, () => api.recon.decide(p.id, "accept"), `${p.id} accepted and sent for approval`)}>
                        Accept
                      </Button>
                      <Button size="small" color="error" disabled={busy !== null} onClick={() => act(p.id, () => api.recon.decide(p.id, "reject"), `${p.id} rejected`)}>
                        Reject
                      </Button>
                    </Stack>
                  ),
                },
              ]}
            />
          </Panel>
          <Panel title="Recent decisions">
            <DataTable<LearningDecision>
              rows={s.recent}
              rowKey={(d) => `${d.match}-${d.at}`}
              empty="No decisions yet."
              columns={[
                { key: "t", header: "Time", render: (d) => when(d.at) },
                { key: "m", header: "Match", render: (d) => <span style={mono}>{d.match}</span> },
                { key: "w", header: "By", render: (d) => d.actor.split("@")[0] },
                { key: "o", header: "Outcome", render: (d) => <StatusPill label={d.outcome} tone={d.outcome === "Accepted" ? "ok" : "crit"} /> },
                { key: "s", header: "Step", render: (d) => SOURCE[d.source ?? "legacy"] ?? d.source },
                { key: "p", header: "Model said", align: "right", render: (d) => <span style={mono}>{(100 * d.modelScore).toFixed(0)}%</span> },
              ]}
            />
          </Panel>
        </Stack>
        <Stack spacing={2.5}>
          <Panel title="Next model">
            <KeyValue label="Decisions needed" value={`${s.labels.usable} of ${s.labels.minimum}`} />
            <LinearProgress variant="determinate" value={progress} sx={{ my: 1.25, height: 6, borderRadius: 3 }} />
            <KeyValue label="Method" value="Adapter on the shipped scorer" />
            <KeyValue label="Proof" value="Error ≤ 0.5% at 95% confidence" />
            <KeyValue label="Release" value="Controller promotes · four eyes" />
            <Typography sx={{ fontSize: 12, color: "text.secondary", my: 1.5 }}>
              Training takes a few minutes in the background. The result appears under Models with its evidence; nothing
              changes until it is promoted.
            </Typography>
            <Button
              size="small"
              variant="contained"
              disabled={!s.canTrain || busy !== null}
              onClick={() => act("train", api.learning.train, "Training started. The candidate will appear under Models.")}
            >
              {training ? "Training…" : "Train a new model"}
            </Button>
          </Panel>
          <Panel title="Are reviewers agreeing with the model?">
            {outcomes.status === "unknown" ? (
              <Typography sx={{ fontSize: 12, color: "text.secondary" }}>
                Needs 30 decisions; {outcomes.decisions} so far.
              </Typography>
            ) : (
              <>
                <KeyValue label="Model expected accepted" value={`${(100 * (outcomes.expected_accept_rate ?? 0)).toFixed(0)}%`} />
                <KeyValue label="Reviewers accepted" value={`${(100 * (outcomes.actual_accept_rate ?? 0)).toFixed(0)}%`} />
                <KeyValue label="Status" value={<StatusPill label={outcomes.status} tone={outcomes.status === "ok" ? "ok" : outcomes.status === "watch" ? "warn" : "crit"} />} />
              </>
            )}
          </Panel>
          <Panel title="Where decisions come from">
            {Object.keys(s.labels.bySource).length === 0 ? (
              <Typography sx={{ fontSize: 12, color: "text.secondary" }}>Nothing recorded yet.</Typography>
            ) : (
              Object.entries(s.labels.bySource).map(([k, v]) => <KeyValue key={k} label={SOURCE[k] ?? k} value={v.toLocaleString()} />)
            )}
          </Panel>
        </Stack>
      </Box>
      {toastNode}
    </>
  );
}
