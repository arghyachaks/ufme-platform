import { useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Box, Button, Chip, MenuItem, Stack, TextField, Typography } from "@mui/material";
import { api, ApiError } from "../../api/services";
import { useQuery } from "../../api/useQuery";
import type { ExceptionItem } from "../../api/types";
import { Panel, StatusPill } from "../../components/common/Panel";
import { DataTable, Meter, Page, StatGrid, money, mono, severityTone, useToast } from "../../components/common/Blocks";

const agingBuckets = [
  { label: "0–3 d", test: (d: number) => d <= 3 },
  { label: "4–7 d", test: (d: number) => d > 3 && d <= 7 },
  { label: "8–15 d", test: (d: number) => d > 7 && d <= 15 },
  { label: "16–30 d", test: (d: number) => d > 15 && d <= 30 },
  { label: "> 30 d", test: (d: number) => d > 30 },
];

export function ExceptionsDashboardPage() {
  const { data = [], loading, reload } = useQuery(api.exceptions.list);
  const navigate = useNavigate();
  const { toast, toastNode } = useToast();
  const [severity, setSeverity] = useState("All");
  const [type, setType] = useState("All");
  const [checked, setChecked] = useState<string[]>([]);

  const open = data.filter((e) => e.status !== "Resolved");
  const rows = useMemo(
    () => open.filter((e) => (severity === "All" || e.severity === severity) && (type === "All" || e.type === type))
      .sort((a, b) => b.amount - a.amount),
    [open, severity, type],
  );
  const breaching = open.filter((e) => e.slaHoursLeft < 0).length;
  const exposure = open.reduce((s, e) => s + e.amount, 0);
  const byCause = Object.entries(open.reduce<Record<string, number>>((acc, e) => ((acc[e.rootCause] = (acc[e.rootCause] ?? 0) + 1), acc), {}))
    .sort((a, b) => b[1] - a[1]);
  const byOwner = Object.entries(open.reduce<Record<string, number>>((acc, e) => ((acc[e.owner] = (acc[e.owner] ?? 0) + 1), acc), {}));

  const plural = (n: number) => `${n} exception${n > 1 ? "s" : ""}`;
  const fail = (e: unknown) => toast(e instanceof ApiError ? e.message : String(e));
  const bulk = async (label: "Investigating" | "Escalated" | "Case") => {
    const ids = checked;
    setChecked([]);
    try {
      if (label === "Case") {
        const c = await api.workflow.createCase(ids);
        toast(`${c.id} opened for ${plural(ids.length)}`);
        navigate("/exceptions/cases");
        return;
      }
      await Promise.all(ids.map((id) => api.workflow.setExceptionStatus(id, label)));
      toast(`${label === "Escalated" ? "Escalated" : "Started investigating"} ${plural(ids.length)}`);
    } catch (e) {
      fail(e);
    }
    reload();
  };

  return (
    <Page
      title="Exceptions"
      description="Unmatched and variance items across all reconciliations, prioritised by exposure and SLA risk."
      loading={loading}
      actions={<Button variant="contained" onClick={() => navigate("/exceptions/cases")}>Open case board</Button>}
    >
      <StatGrid items={[
        { label: "Open exceptions", value: String(open.length), hint: "412 across all tenants" },
        { label: "Exposure", value: money(exposure), tone: "warn" },
        { label: "SLA breached", value: String(breaching), tone: breaching ? "crit" : "ok", hint: "Past due now" },
        { label: "Avg age", value: `${(open.reduce((s, e) => s + e.ageDays, 0) / Math.max(open.length, 1)).toFixed(1)} d` },
        { label: "Auto-resolved (7d)", value: "1,184", tone: "ok", hint: "By rules & AI" },
      ]} />

      <Box sx={{ display: "grid", gridTemplateColumns: { xs: "1fr", lg: "1fr 1fr 1fr" }, gap: 2.5 }}>
        <Panel title="Aging">
          <Stack spacing={1.25}>
            {agingBuckets.map((b) => {
              const n = open.filter((e) => b.test(e.ageDays)).length;
              return (
                <Stack key={b.label} direction="row" alignItems="center" spacing={1.5}>
                  <Typography sx={{ fontSize: 12, width: 60 }}>{b.label}</Typography>
                  <Box sx={{ flex: 1 }}><Meter value={n} max={Math.max(open.length, 1)} tone={b.label.startsWith(">") || b.label.startsWith("16") ? "crit" : "ok"} /></Box>
                  <Typography sx={{ ...mono, fontSize: 12, width: 24, textAlign: "right" }}>{n}</Typography>
                </Stack>
              );
            })}
          </Stack>
        </Panel>
        <Panel title="Root causes">
          <Stack spacing={1}>
            {byCause.map(([cause, n]) => (
              <Stack key={cause} direction="row" justifyContent="space-between">
                <Typography sx={{ fontSize: 12 }}>{cause}</Typography>
                <Chip size="small" label={n} />
              </Stack>
            ))}
          </Stack>
        </Panel>
        <Panel title="Assignment load">
          <Stack spacing={1.25}>
            {byOwner.map(([owner, n]) => (
              <Stack key={owner} direction="row" alignItems="center" spacing={1.5}>
                <Typography sx={{ fontSize: 12, width: 100, color: owner === "Unassigned" ? "error.main" : "text.primary" }}>{owner}</Typography>
                <Box sx={{ flex: 1 }}><Meter value={n} max={8} /></Box>
                <Typography sx={{ ...mono, fontSize: 12 }}>{n}</Typography>
              </Stack>
            ))}
          </Stack>
        </Panel>
      </Box>

      <Stack direction={{ xs: "column", md: "row" }} spacing={1} alignItems={{ md: "center" }} justifyContent="space-between">
        <Stack direction="row" spacing={1}>
          <TextField select size="small" label="Severity" value={severity} onChange={(e) => setSeverity(e.target.value)} sx={{ minWidth: 130 }}>
            {["All", "Critical", "High", "Medium", "Low"].map((s) => <MenuItem key={s} value={s}>{s}</MenuItem>)}
          </TextField>
          <TextField select size="small" label="Type" value={type} onChange={(e) => setType(e.target.value)} sx={{ minWidth: 170 }}>
            {["All", "Unmatched", "Amount variance", "Duplicate", "FX difference", "Timing", "Missing document"].map((s) => <MenuItem key={s} value={s}>{s}</MenuItem>)}
          </TextField>
        </Stack>
        <Stack direction="row" spacing={1}>
          <Button size="small" variant="outlined" disabled={!checked.length} onClick={() => void bulk("Investigating")}>Start investigating</Button>
          <Button size="small" variant="outlined" disabled={!checked.length} onClick={() => void bulk("Case")}>Create case</Button>
          <Button size="small" variant="outlined" color="error" disabled={!checked.length} onClick={() => void bulk("Escalated")}>Escalate</Button>
        </Stack>
      </Stack>

      <DataTable<ExceptionItem>
        rows={rows}
        rowKey={(r) => r.id}
        selectable
        checked={checked}
        onCheckedChange={setChecked}
        onRowClick={(r) => navigate(`/exceptions/investigations?id=${r.id}`)}
        columns={[
          { key: "id", header: "ID", render: (r) => <Typography sx={{ ...mono, fontSize: 12, fontWeight: 700 }}>{r.id}</Typography> },
          { key: "pair", header: "Entity ↔ Counterparty", render: (r) => `${r.entity} ↔ ${r.counterparty}` },
          { key: "type", header: "Type", render: (r) => r.type },
          { key: "amt", header: "Amount", align: "right", render: (r) => <span style={mono}>{money(r.amount, r.currency)}</span> },
          { key: "sev", header: "Severity", render: (r) => <StatusPill label={r.severity} tone={severityTone[r.severity]} /> },
          { key: "age", header: "Age", render: (r) => `${r.ageDays} d` },
          { key: "sla", header: "SLA", render: (r) => <Typography sx={{ fontSize: 12, fontWeight: 600, color: r.slaHoursLeft < 0 ? "error.main" : r.slaHoursLeft < 12 ? "warning.main" : "text.primary" }}>{r.slaHoursLeft < 0 ? `${-r.slaHoursLeft}h overdue` : `${r.slaHoursLeft}h left`}</Typography> },
          { key: "owner", header: "Owner", render: (r) => r.owner },
          { key: "status", header: "Status", render: (r) => r.status },
        ]}
      />
      {toastNode}
    </Page>
  );
}
