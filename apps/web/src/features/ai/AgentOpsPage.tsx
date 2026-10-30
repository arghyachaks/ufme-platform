import { useMemo, useState } from "react";
import { Box, Drawer, IconButton, MenuItem, Select, Stack, Typography } from "@mui/material";
import CloseRoundedIcon from "@mui/icons-material/CloseRounded";
import { api } from "../../api/services";
import { useQuery } from "../../api/useQuery";
import type { AgentOverview, AgentRunDetail, AgentRunRow } from "../../api/types";
import { Panel, StatusPill } from "../../components/common/Panel";
import { DataTable, KeyValue, Page, PageSkeleton, StatGrid, mono } from "../../components/common/Blocks";
import { AgentWork, answerText, applyEvent, emptyWork } from "../../components/shell/AgentWork";

const n = (v: number) => v.toLocaleString();
const usd = (v: number) => (v ? `$${v.toFixed(v < 1 ? 4 : 2)}` : "$0");
const secs = (ms: number | null) => (ms == null ? "—" : `${(ms / 1000).toFixed(1)}s`);
const when = (iso: string) => new Date(iso).toLocaleString(undefined, { day: "2-digit", month: "short", hour: "2-digit", minute: "2-digit" });
const STATUS_TONE: Record<AgentRunRow["status"], "ok" | "warn" | "crit"> = { completed: "ok", running: "warn", fallback: "warn", cancelled: "warn", failed: "crit" };
const SEV_TONE = { High: "crit", Medium: "warn", Low: "ok" } as const;

export function AgentOpsPage() {
  const [days, setDays] = useState(7);
  const q = useQuery(() => api.agents.overview(days), [days]);
  return (
    <Page
      title="Agent operations"
      description="What the agents did: usage, which models they ran on, anomalies, and the security and model-risk evidence. Agents only read and propose; every change goes through approval."
      actions={
        <Select size="small" value={days} onChange={(e) => setDays(Number(e.target.value))} aria-label="Period">
          {[1, 7, 30, 90].map((d) => <MenuItem key={d} value={d}>{d === 1 ? "Last 24 hours" : `Last ${d} days`}</MenuItem>)}
        </Select>
      }
      loading={q.loading && !q.data}
    >
      {q.data ? <OpsView o={q.data} /> : <PageSkeleton />}
    </Page>
  );
}

function OpsView({ o }: { o: AgentOverview }) {
  const [runId, setRunId] = useState<string | null>(null);
  const t = o.totals;
  const maxDay = Math.max(1, ...o.byDay.map((d) => d.runs));
  return (
    <Stack spacing={2}>
      {o.scope === "mine" && <Typography sx={{ fontSize: 13, color: "text.secondary" }}>Showing your own runs. Controllers, Finance Directors and Auditors see every run in the tenant.</Typography>}
      <StatGrid
        items={[
          { label: "Agent runs", value: n(t.runs), hint: `${t.completed} completed · ${t.fallback} fallback · ${t.failed} failed`, tone: t.failed ? "crit" : undefined },
          { label: "Tokens", value: n(t.tokensIn + t.tokensOut), hint: `${n(t.tokensIn)} in · ${n(t.tokensOut)} out` },
          { label: "Cost", value: usd(t.costUsd), hint: o.infosec.localOnly ? "all on-premise" : "includes hosted models" },
          { label: "Work done", value: n(t.toolCalls), hint: `lookups · ${t.subagents} sub-agents · avg ${secs(t.avgMs)}` },
          { label: "Data sent outside", value: n(t.egressRuns), hint: t.egressRuns ? "runs on hosted models" : "no data left the network", tone: t.egressRuns ? "warn" : "ok" },
        ]}
      />

      <Box sx={{ display: "grid", gridTemplateColumns: { xs: "1fr", lg: "3fr 2fr" }, gap: 2 }}>
        <Panel title={`Anomalies (${o.anomalies.length})`}>
          {o.anomalies.length === 0 ? (
            <Typography sx={{ fontSize: 13, color: "text.secondary" }}>Nothing unusual in this period.</Typography>
          ) : (
            <Stack spacing={0.75}>
              {o.anomalies.map((a, i) => (
                <Stack key={i} direction="row" spacing={1.25} alignItems="center" sx={{ cursor: a.run ? "pointer" : "default" }} onClick={() => a.run && setRunId(a.run)}>
                  <StatusPill label={a.severity} tone={SEV_TONE[a.severity]} />
                  <Typography sx={{ fontSize: 13, fontWeight: 600, minWidth: 140 }}>{a.kind}</Typography>
                  <Typography sx={{ fontSize: 13, color: "text.secondary" }}>{a.detail}</Typography>
                </Stack>
              ))}
            </Stack>
          )}
        </Panel>
        <Panel title="Security and controls">
          <KeyValue label="Autonomous actions" value={`${o.infosec.autonomousActions} (agents only propose)`} />
          <KeyValue label="Agent write tools" value={o.infosec.writeTools} />
          <KeyValue label="Data egress" value={o.infosec.localOnly ? "None: on-premise models only" : Object.entries(o.infosec.egressByProvider).map(([p, c]) => `${p} ${c}`).join(" · ")} />
          <KeyValue label="Hosted models approved" value={o.infosec.hostedModelsApproved.length ? o.infosec.hostedModelsApproved.join(", ") : "None"} />
          <KeyValue label="Run evidence" value="Every step recorded and replayable" />
        </Panel>
      </Box>

      <Box sx={{ display: "grid", gridTemplateColumns: { xs: "1fr", lg: "1fr 1fr" }, gap: 2 }}>
        <Panel title="Usage by model">
          <DataTable
            rows={o.byModel}
            rowKey={(r) => r.model}
            empty="No runs yet."
            columns={[
              { key: "m", header: "Model", render: (r) => <span style={mono}>{r.model}</span> },
              { key: "p", header: "Provider", render: (r) => r.provider },
              { key: "r", header: "Runs", align: "right", render: (r) => n(r.runs) },
              { key: "t", header: "Tokens", align: "right", render: (r) => n(r.tokens) },
              { key: "c", header: "Cost", align: "right", render: (r) => usd(r.costUsd) },
            ]}
          />
          {o.byDay.length > 0 && (
            <Stack direction="row" spacing={0.5} alignItems="flex-end" sx={{ height: 64, mt: 2 }} aria-label="Runs per day">
              {o.byDay.map((d) => (
                <Box key={d.day} title={`${d.day}: ${d.runs} runs, ${n(d.tokens)} tokens`} sx={{ flex: 1, bgcolor: "var(--brand-indigo)", height: `${Math.max(4, (100 * d.runs) / maxDay)}%`, borderRadius: "1px" }} />
              ))}
            </Stack>
          )}
        </Panel>
        <Panel title="Usage by person">
          <DataTable
            rows={o.byUser}
            rowKey={(r) => r.actor}
            empty="No runs yet."
            columns={[
              { key: "a", header: "Person", render: (r) => r.actor },
              { key: "r", header: "Runs", align: "right", render: (r) => n(r.runs) },
              { key: "t", header: "Tokens", align: "right", render: (r) => n(r.tokens) },
              { key: "c", header: "Cost", align: "right", render: (r) => usd(r.costUsd) },
            ]}
          />
        </Panel>
      </Box>

      <Panel title="Model inventory">
        <DataTable
          rows={o.models}
          rowKey={(r) => r.name}
          columns={[
            { key: "n", header: "Name", render: (r) => <span style={mono}>{r.name}</span> },
            { key: "p", header: "Provider · model", render: (r) => `${r.provider} · ${r.model}` },
            { key: "w", header: "Runs where", render: (r) => (r.local ? "On-premise" : "Hosted (data leaves network)") },
            { key: "s", header: "Status", render: (r) => <StatusPill label={r.status === "approved" ? "Approved" : "Blocked"} tone={r.status === "approved" ? "ok" : "warn"} /> },
            { key: "b", header: "Used by", render: (r) => (r.bindings?.length ? r.bindings.join(", ") : "—") },
            { key: "c", header: "Price / 1K tokens", align: "right", render: (r) => (r.priceIn || r.priceOut ? `$${r.priceIn} in · $${r.priceOut} out` : "Free (local)") },
            { key: "k", header: "Key", render: (r) => (r.keyConfigured == null ? "Not needed" : r.keyConfigured ? "Configured" : "Missing") },
          ]}
        />
      </Panel>

      <Panel title="Recent runs">
        <DataTable
          rows={o.recent}
          rowKey={(r) => r.id}
          onRowClick={(r) => setRunId(r.id)}
          empty="No agent runs yet. Ask ufme Assist a question to start one."
          columns={[
            { key: "w", header: "When", render: (r) => when(r.startedAt) },
            { key: "a", header: "Agent", render: (r) => r.agent },
            { key: "u", header: "Person", render: (r) => r.actor },
            { key: "q", header: "Question", render: (r) => <Box sx={{ maxWidth: 360, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{r.question}</Box> },
            { key: "m", header: "Model", render: (r) => <span style={mono}>{r.model}</span> },
            { key: "s", header: "Status", render: (r) => <StatusPill label={r.status} tone={STATUS_TONE[r.status]} /> },
            { key: "st", header: "Steps", align: "right", render: (r) => r.toolCalls + r.subagents },
            { key: "t", header: "Tokens", align: "right", render: (r) => n(r.tokensIn + r.tokensOut) },
            { key: "d", header: "Time", align: "right", render: (r) => secs(r.ms) },
          ]}
        />
      </Panel>
      <RunDrawer id={runId} onClose={() => setRunId(null)} />
    </Stack>
  );
}

function RunDrawer({ id, onClose }: { id: string | null; onClose: () => void }) {
  const q = useQuery<AgentRunDetail | null>(() => (id ? api.agents.run(id) : Promise.resolve(null)), [id]);
  const work = useMemo(() => (q.data ? q.data.events.reduce(applyEvent, emptyWork()) : null), [q.data]);
  return (
    <Drawer anchor="right" open={Boolean(id)} onClose={onClose} PaperProps={{ sx: { width: { xs: "100%", sm: 520 }, p: 2.5 } }}>
      <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ mb: 1.5 }}>
        <Typography variant="h6" sx={{ fontSize: 20 }}>Run replay</Typography>
        <IconButton aria-label="Close" onClick={onClose}><CloseRoundedIcon /></IconButton>
      </Stack>
      {q.error && <Typography sx={{ color: "text.secondary" }}>{q.error}</Typography>}
      {q.data && work && (
        <Stack spacing={1.5}>
          <KeyValue label="Asked by" value={q.data.actor} />
          <KeyValue label="When" value={when(q.data.startedAt)} />
          <KeyValue label="Model" value={`${q.data.model} (${q.data.provider})`} />
          <KeyValue label="Status" value={q.data.status} />
          {q.data.error && <KeyValue label="Error" value={q.data.error} />}
          <Box>
            <Typography sx={{ ...mono, fontSize: 11, mb: 0.5 }}>QUESTION</Typography>
            <Typography sx={{ fontSize: 13.5 }}>{q.data.question}</Typography>
          </Box>
          <AgentWork w={{ ...work, finished: false, answer: undefined }} />
          <Box>
            <Typography sx={{ ...mono, fontSize: 11, mb: 0.5 }}>ANSWER</Typography>
            <Typography sx={{ fontSize: 13.5, whiteSpace: "pre-wrap" }}>{answerText(work) || "—"}</Typography>
          </Box>
        </Stack>
      )}
    </Drawer>
  );
}
