import { useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Box, Button, Chip, Drawer, LinearProgress, Stack, Typography } from "@mui/material";
import { api, ApiError } from "../../api/services";
import { useQuery } from "../../api/useQuery";
import type { BatchDetail, DataSource, IngestionBatch } from "../../api/types";
import { Panel, StatusPill } from "../../components/common/Panel";
import { DataTable, KeyValue, Page, StatGrid, glass, mono, useToast } from "../../components/common/Blocks";

const tone = { Healthy: "ok", Degraded: "warn", Failed: "crit", Paused: "warn" } as const;
const batchTone = { Completed: "ok", Processing: "warn", Queued: "warn", Failed: "crit" } as const;

const wait = (ms: number) => new Promise((r) => setTimeout(r, ms));

export function SourcesPage() {
  const sources = useQuery(api.data.sources);
  const batches = useQuery(() => api.data.batches());
  const { toast, toastNode } = useToast();
  const navigate = useNavigate();
  const fileInput = useRef<HTMLInputElement>(null);
  const [uploadFor, setUploadFor] = useState<string | null>(null);
  const [busy, setBusy] = useState<string | null>(null);
  const [detail, setDetail] = useState<BatchDetail | null>(null);
  const data = sources.data ?? [];
  const total = data.reduce((s, d) => s + d.records24h, 0);

  const follow = async (started: IngestionBatch) => {
    let batch: BatchDetail = await api.data.batch(started.id);
    for (let i = 0; i < 120 && (batch.status === "Queued" || batch.status === "Processing"); i++) {
      await wait(1000);
      batch = await api.data.batch(started.id);
    }
    sources.reload();
    batches.reload();
    toast(
      batch.status === "Completed"
        ? `${batch.id}: ${batch.rowsLoaded.toLocaleString()} loaded, ${batch.rowsQuarantined.toLocaleString()} quarantined`
        : `${batch.id} ${batch.status}${batch.error ? ` — ${batch.error}` : ""}`,
    );
  };

  const run = async (code: string, action: () => Promise<IngestionBatch>) => {
    setBusy(code);
    try {
      await follow(await action());
    } catch (err) {
      toast(err instanceof ApiError ? err.message : "Request failed");
    } finally {
      setBusy(null);
    }
  };

  const onFile = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    const code = uploadFor;
    event.target.value = "";
    if (file && code) void run(code, () => api.data.upload(code, file));
  };

  const openBatch = async (row: IngestionBatch) => setDetail(await api.data.batch(row.id));

  return (
    <Page title="Data sources" description="ERP, bank, file, and API connectors feeding the matching engine. Every load is validated, normalized, FX-enriched, and quarantined where it fails checks." loading={sources.loading}
      actions={<Button variant="outlined" onClick={() => navigate("/data/quality")}>Data quality</Button>}>
      <input ref={fileInput} type="file" accept=".csv,.tsv,.txt" hidden onChange={onFile} />
      <StatGrid items={[
        { label: "Connectors", value: String(data.length) },
        { label: "Healthy", value: String(data.filter((d) => d.status === "Healthy").length), tone: "ok" },
        { label: "Needs attention", value: String(data.filter((d) => d.status === "Failed" || d.status === "Degraded").length), tone: "crit" },
        { label: "Records (24h)", value: total.toLocaleString() },
      ]} />
      <Box sx={{ display: "grid", gridTemplateColumns: { xs: "1fr", md: "1fr 1fr", xl: "1fr 1fr 1fr" }, gap: 2 }}>
        {data.map((s: DataSource) => (
          <Box key={s.id} sx={{ ...glass, p: 2, borderLeft: "4px solid", borderLeftColor: s.status === "Healthy" ? "success.main" : s.status === "Failed" ? "error.main" : "warning.main" }}>
            <Stack direction="row" justifyContent="space-between" alignItems="flex-start">
              <Box>
                <Typography sx={{ fontSize: 13, fontWeight: 700 }}>{s.name}</Typography>
                <Typography sx={{ fontSize: 11, color: "text.secondary" }}>{s.system} · {s.id}</Typography>
              </Box>
              <Stack direction="row" spacing={0.5}><Chip size="small" label={s.kind} variant="outlined" /><StatusPill label={s.status} tone={tone[s.status]} /></Stack>
            </Stack>
            <Box sx={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 1, my: 1.5 }}>
              {[["Last sync", s.lastSync], ["Records 24h", s.records24h.toLocaleString()], ["Schedule", s.schedule]].map(([k, v]) => (
                <Box key={k}><Typography sx={{ fontSize: 10, color: "text.secondary", textTransform: "uppercase" }}>{k}</Typography><Typography sx={{ ...mono, fontSize: 12, fontWeight: 600 }}>{v}</Typography></Box>
              ))}
            </Box>
            {busy === s.id ? <LinearProgress sx={{ mb: 1 }} /> : null}
            <Stack direction="row" spacing={1}>
              {s.kind !== "File" ? (
                <Button size="small" variant="outlined" disabled={Boolean(busy) || s.status === "Paused"} onClick={() => run(s.id, () => api.data.sync(s.id))}>Sync now</Button>
              ) : null}
              <Button size="small" variant={s.kind === "File" ? "outlined" : "text"} disabled={Boolean(busy) || s.status === "Paused"}
                onClick={() => { setUploadFor(s.id); fileInput.current?.click(); }}>Upload file</Button>
            </Stack>
          </Box>
        ))}
      </Box>

      <Panel title="Recent loads">
        <DataTable<IngestionBatch> rows={batches.data ?? []} rowKey={(b) => b.id} onRowClick={openBatch} empty="No loads yet — sync a source or upload a file." columns={[
          { key: "id", header: "Batch", render: (b) => <span style={{ ...mono, fontWeight: 700 }}>{b.id}</span> },
          { key: "s", header: "Source", render: (b) => b.source },
          { key: "f", header: "File", render: (b) => b.fileName },
          { key: "st", header: "Status", render: (b) => <StatusPill label={b.status} tone={batchTone[b.status]} /> },
          { key: "t", header: "Rows", align: "right", render: (b) => b.rowsTotal.toLocaleString() },
          { key: "l", header: "Loaded", align: "right", render: (b) => b.rowsLoaded.toLocaleString() },
          { key: "q", header: "Quarantined", align: "right", render: (b) => <Typography sx={{ fontSize: 12, color: b.rowsQuarantined ? "error.main" : "text.primary" }}>{b.rowsQuarantined.toLocaleString()}</Typography> },
          { key: "d", header: "Duration", align: "right", render: (b) => (b.durationMs != null ? `${(b.durationMs / 1000).toFixed(1)} s` : "—") },
          { key: "a", header: "Started", render: (b) => b.startedAt ?? "—" },
        ]} />
      </Panel>

      <Drawer anchor="right" open={Boolean(detail)} onClose={() => setDetail(null)}>
        {detail ? (
          <Box sx={{ width: { xs: "100vw", sm: 520 }, p: 3 }}>
            <Typography sx={{ ...mono, fontSize: 12, color: "text.secondary" }}>{detail.id}</Typography>
            <Typography variant="h6" sx={{ fontSize: 17, mb: 2 }}>{detail.fileName}</Typography>
            <KeyValue label="Source" value={detail.source} />
            <KeyValue label="Status" value={<StatusPill label={detail.status} tone={batchTone[detail.status]} />} />
            <KeyValue label="Rows / loaded / quarantined" value={`${detail.rowsTotal.toLocaleString()} / ${detail.rowsLoaded.toLocaleString()} / ${detail.rowsQuarantined.toLocaleString()}`} />
            <KeyValue label="Duration" value={detail.durationMs != null ? `${(detail.durationMs / 1000).toFixed(1)} s` : "—"} />
            {detail.error ? <Typography sx={{ fontSize: 12, color: "error.main", mt: 1.5 }}>{detail.error}</Typography> : null}
            <Typography variant="subtitle2" sx={{ mt: 2.5, mb: 1 }}>Quality findings</Typography>
            {detail.issues.length === 0 ? <Typography sx={{ fontSize: 12, color: "text.secondary" }}>None.</Typography> : null}
            {detail.issues.map((i) => (
              <Stack key={i.id} direction="row" justifyContent="space-between" sx={{ py: 0.5 }}>
                <Typography sx={{ fontSize: 12 }}>{i.check}</Typography>
                <Typography sx={{ ...mono, fontSize: 12, color: i.autoFixed ? "success.main" : "text.primary" }}>{i.failing.toLocaleString()}{i.autoFixed ? " fixed" : ""}</Typography>
              </Stack>
            ))}
            <Typography variant="subtitle2" sx={{ mt: 2.5, mb: 1 }}>Quarantined rows (first {detail.quarantined.length})</Typography>
            <Stack spacing={1}>
              {detail.quarantined.map((q) => (
                <Box key={q.line} sx={{ p: 1, borderRadius: 1, bgcolor: "var(--crimson-soft)" }}>
                  <Typography sx={{ fontSize: 11, fontWeight: 700 }}>Line {q.line}: {q.errors.join(", ")}</Typography>
                  <Typography sx={{ ...mono, fontSize: 11, wordBreak: "break-all" }}>{Object.values(q.raw).join(" | ")}</Typography>
                </Box>
              ))}
            </Stack>
          </Box>
        ) : null}
      </Drawer>
      {toastNode}
    </Page>
  );
}
