import { Box, Button, Typography } from "@mui/material";
import { api } from "../../api/services";
import { useQuery } from "../../api/useQuery";
import type { JobRun, ServiceHealth } from "../../api/types";
import { Panel, StatusPill } from "../../components/common/Panel";
import { DataTable, Meter, Page, Sparkline, StatGrid, mono, useToast } from "../../components/common/Blocks";

const jobTone = { Running: "warn", Succeeded: "ok", Failed: "crit", Queued: "warn" } as const;

export function OperationsPage() {
  const { data, loading } = useQuery(api.ops.all);
  const { toast, toastNode } = useToast();
  return (
    <Page title="Operations" description="Service health, scaling, background jobs, and throughput for platform operators." loading={loading}>
      {data ? (
        <>
          <StatGrid items={[
            { label: "Services healthy", value: `${data.services.filter((s) => s.status === "ok").length}/${data.services.length}`, tone: "warn" },
            { label: "Throughput", value: "18.4K tx/min", tone: "ok" },
            { label: "p95 match latency", value: "212 ms" },
            { label: "Failed jobs (24h)", value: String(data.jobs.filter((j) => j.status === "Failed").length), tone: "crit" },
          ]} />
          <Box sx={{ display: "grid", gridTemplateColumns: { xs: "1fr", md: "1fr 1fr" }, gap: 2.5 }}>
            <Panel title="Throughput · last 12h"><Sparkline values={[12.1, 13.4, 12.8, 15.2, 16.9, 18.1, 17.4, 18.8, 19.6, 18.2, 18.9, 18.4]} /></Panel>
            <Panel title="Error rate · last 12h"><Sparkline values={[0.2, 0.1, 0.3, 0.2, 0.2, 0.4, 0.9, 0.5, 0.3, 0.2, 0.3, 0.2]} color="var(--brand-crimson)" /></Panel>
          </Box>
          <DataTable<ServiceHealth> rows={data.services} rowKey={(s) => s.name} columns={[
            { key: "n", header: "Service", render: (s) => <b style={mono}>{s.name}</b> },
            { key: "s", header: "Status", render: (s) => <StatusPill label={s.status === "ok" ? "Healthy" : s.status === "warn" ? "Degraded" : "Down"} tone={s.status} /> },
            { key: "l", header: "Latency", align: "right", render: (s) => (s.latencyMs ? `${s.latencyMs} ms` : "—") },
            { key: "c", header: "CPU", render: (s) => <Meter value={s.cpu} label={`${s.cpu}%`} /> },
            { key: "m", header: "Memory", render: (s) => <Meter value={s.memory} label={`${s.memory}%`} /> },
            { key: "r", header: "Replicas", render: (s) => s.replicas },
            { key: "u", header: "Uptime (30d)", render: (s) => s.uptime },
            { key: "a", header: "", render: (s) => <Button size="small" onClick={() => toast(`Scaling ${s.name} +1 replica`)}>Scale</Button> },
          ]} />
          <Panel title="Background jobs">
            <DataTable<JobRun> rows={data.jobs} rowKey={(j) => j.id} columns={[
              { key: "id", header: "Job", render: (j) => <><Typography sx={{ fontSize: 12, fontWeight: 600 }}>{j.job}</Typography><Typography sx={{ ...mono, fontSize: 11, color: "text.secondary" }}>{j.id}</Typography></> },
              { key: "s", header: "Status", render: (j) => <StatusPill label={j.status} tone={jobTone[j.status]} /> },
              { key: "st", header: "Started", render: (j) => j.started },
              { key: "d", header: "Duration", render: (j) => j.duration },
              { key: "r", header: "Records", align: "right", render: (j) => j.records.toLocaleString() },
              { key: "a", header: "", render: (j) => (j.status === "Failed" ? <Button size="small" onClick={() => toast(`${j.id} retried`)}>Retry</Button> : null) },
            ]} />
          </Panel>
        </>
      ) : null}
      {toastNode}
    </Page>
  );
}
