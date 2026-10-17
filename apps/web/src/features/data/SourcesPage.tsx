import { Box, Button, Chip, Stack, Typography } from "@mui/material";
import { api } from "../../api/services";
import { useQuery } from "../../api/useQuery";
import type { DataSource } from "../../api/types";
import { StatusPill } from "../../components/common/Panel";
import { Page, StatGrid, glass, mono, useToast } from "../../components/common/Blocks";

const tone = { Healthy: "ok", Degraded: "warn", Failed: "crit", Paused: "warn" } as const;

export function SourcesPage() {
  const { data = [], loading } = useQuery(api.data.sources);
  const { toast, toastNode } = useToast();
  const total = data.reduce((s, d) => s + d.records24h, 0);
  return (
    <Page title="Data sources" description="ERP, bank, file, and API connectors feeding the matching engine, with sync health and volume." loading={loading}
      actions={<Button variant="contained" onClick={() => toast("Connector catalog opened: SAP, Oracle, NetSuite, Workday, SWIFT, SFTP, REST")}>Add connector</Button>}>
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
                <Typography sx={{ fontSize: 11, color: "text.secondary" }}>{s.system}</Typography>
              </Box>
              <Stack direction="row" spacing={0.5}><Chip size="small" label={s.kind} variant="outlined" /><StatusPill label={s.status} tone={tone[s.status]} /></Stack>
            </Stack>
            <Box sx={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 1, my: 1.5 }}>
              {[["Last sync", s.lastSync], ["Records 24h", s.records24h.toLocaleString()], ["Schedule", s.schedule]].map(([k, v]) => (
                <Box key={k}><Typography sx={{ fontSize: 10, color: "text.secondary", textTransform: "uppercase" }}>{k}</Typography><Typography sx={{ ...mono, fontSize: 12, fontWeight: 600 }}>{v}</Typography></Box>
              ))}
            </Box>
            <Stack direction="row" spacing={1}>
              <Button size="small" variant="outlined" onClick={() => toast(`Sync started for ${s.name}`)}>Sync now</Button>
              {s.status === "Failed" ? <Button size="small" color="error" onClick={() => toast("Error log: schema mismatch — column 'net_pay' missing")}>View error</Button> : null}
              <Button size="small" onClick={() => toast(`${s.name} ${s.status === "Paused" ? "resumed" : "paused"}`)}>{s.status === "Paused" ? "Resume" : "Pause"}</Button>
            </Stack>
          </Box>
        ))}
      </Box>
      {toastNode}
    </Page>
  );
}
