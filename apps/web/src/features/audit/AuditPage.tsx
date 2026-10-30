import { useState } from "react";
import { Box, Button, Stack, Tab, Tabs, TextField, Typography } from "@mui/material";
import { api, ApiError } from "../../api/services";
import { useQuery } from "../../api/useQuery";
import type { AuditEvent, ControlTest } from "../../api/types";
import { Panel, StatusPill } from "../../components/common/Panel";
import { DataTable, Page, StatGrid, mono, useToast } from "../../components/common/Blocks";

const resultTone = { Pass: "ok", Fail: "crit", Pending: "warn" } as const;

export function AuditPage() {
  const { data: events = [], loading } = useQuery(api.audit.events);
  const { data: controls = [] } = useQuery(api.audit.controls);
  const [tab, setTab] = useState(0);
  const [q, setQ] = useState("");
  const { toast, toastNode } = useToast();
  const chain = useQuery(api.audit.verify);
  const [exporting, setExporting] = useState(false);
  const exportEvidence = async () => {
    setExporting(true);
    try {
      const { blob, name } = await api.audit.evidence();
      const url = URL.createObjectURL(blob);
      const a = Object.assign(document.createElement("a"), { href: url, download: name });
      a.click();
      URL.revokeObjectURL(url);
      toast("Evidence package downloaded: audit trail, controls, hashed manifest and signature");
    } catch (e) {
      toast(e instanceof ApiError ? e.message : String(e));
    } finally {
      setExporting(false);
    }
  };
  const filtered = events.filter((e) => !q || Object.values(e).join(" ").toLowerCase().includes(q.toLowerCase()));

  return (
    <Page title="Audit & SOX" description="Immutable audit trail of every match decision, override, and configuration change, plus SOX control testing and evidence export." loading={loading}
      actions={<Button variant="contained" disabled={exporting} onClick={() => void exportEvidence()}>{exporting ? "Preparing…" : "Export evidence package"}</Button>}>
      <StatGrid items={[
        { label: "Controls passing", value: `${controls.filter((c) => c.result === "Pass").length}/${controls.length}`, tone: controls.some((c) => c.result === "Fail") ? "warn" : "ok" },
        { label: "Failing controls", value: String(controls.filter((c) => c.result === "Fail").length), tone: "crit" },
        { label: "Audit events", value: chain.data ? chain.data.events.toLocaleString() : "—" },
        {
          label: "Tamper check",
          value: chain.data ? (chain.data.ok ? "Chain intact" : `Broken at #${chain.data.brokenAt}`) : "—",
          hint: chain.data?.ok ? "Every event re-hashed and linked" : chain.data?.reason,
          tone: chain.data ? (chain.data.ok ? "ok" : "crit") : undefined,
        },
      ]} />
      <Tabs value={tab} onChange={(_, v) => setTab(v)}>
        <Tab label="Audit trail" />
        <Tab label="Control testing" />
      </Tabs>
      {tab === 0 ? (
        <>
          <TextField size="small" placeholder="Search actor, object, entity, control…" value={q} onChange={(e) => setQ(e.target.value)} sx={{ maxWidth: 380 }} />
          <DataTable<AuditEvent> rows={filtered} rowKey={(e) => e.id} columns={[
            { key: "t", header: "Timestamp", render: (e) => <span style={mono}>{e.at}</span> },
            { key: "a", header: "Actor", render: (e) => e.actor },
            { key: "x", header: "Action", render: (e) => e.action },
            { key: "o", header: "Object", render: (e) => <span style={mono}>{e.object}</span> },
            { key: "e", header: "Entity", render: (e) => e.entity },
            { key: "c", header: "Control", render: (e) => e.control },
            { key: "id", header: "Event ID", render: (e) => <Typography sx={{ ...mono, fontSize: 11, color: "text.secondary" }}>{e.id}</Typography> },
          ]} />
        </>
      ) : (
        <Box sx={{ display: "grid", gridTemplateColumns: { xs: "1fr", lg: "2fr 1fr" }, gap: 2.5, alignItems: "start" }}>
          <DataTable<ControlTest> rows={controls} rowKey={(c) => c.id} columns={[
            { key: "id", header: "Control", render: (c) => <b style={mono}>{c.id}</b> },
            { key: "n", header: "Description", render: (c) => c.name },
            { key: "o", header: "Owner", render: (c) => c.owner },
            { key: "l", header: "Last run", render: (c) => c.lastRun },
            { key: "r", header: "Result", render: (c) => <StatusPill label={c.result} tone={resultTone[c.result]} /> },
            { key: "e", header: "Evidence", align: "right", render: (c) => c.evidence.toLocaleString() },
          ]} />
          <Panel title="Attention">
            {controls.filter((c) => c.result !== "Pass").map((c) => (
              <Stack key={c.id} sx={{ mb: 1.5 }}>
                <Typography sx={{ fontSize: 12, fontWeight: 700 }}>{c.id} · {c.result}</Typography>
                <Typography sx={{ fontSize: 12, color: "text.secondary" }}>{c.name}</Typography>
                <Button size="small" sx={{ alignSelf: "flex-start" }} onClick={() => toast(`Remediation task opened for ${c.id}`)}>Remediate</Button>
              </Stack>
            ))}
          </Panel>
        </Box>
      )}
      {toastNode}
    </Page>
  );
}
