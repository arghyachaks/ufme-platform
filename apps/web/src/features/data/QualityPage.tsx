import { Box, Button, Stack, Typography } from "@mui/material";
import { api } from "../../api/services";
import { useQuery } from "../../api/useQuery";
import type { QualityIssue } from "../../api/types";
import { Panel, StatusPill } from "../../components/common/Panel";
import { DataTable, Meter, Page, StatGrid, mono, severityTone, useToast } from "../../components/common/Blocks";

export function QualityPage() {
  const { data, loading, reload } = useQuery(api.data.quality);
  const { toast, toastNode } = useToast();
  const avg = data ? data.dimensions.reduce((s, d) => s + d.score, 0) / data.dimensions.length : 0;
  return (
    <Page title="Data quality" description="Validation and normalization checks run on every record before matching. Bad data is fixed automatically where safe, or quarantined." loading={loading}>
      {data ? (
        <>
          <StatGrid items={[
            { label: "DQ score", value: `${avg.toFixed(1)}%`, tone: avg > 95 ? "ok" : "warn" },
            { label: "Open issues", value: String(data.issues.filter((i) => !i.autoFixed).length), tone: "warn" },
            { label: "Auto-fixed (24h)", value: data.issues.filter((i) => i.autoFixed).reduce((s, i) => s + i.failing, 0).toLocaleString(), tone: "ok" },
            { label: "Quarantined records", value: "1,294", tone: "crit" },
          ]} />
          <Box sx={{ display: "grid", gridTemplateColumns: { xs: "1fr", lg: "1fr 2fr" }, gap: 2.5, alignItems: "start" }}>
            <Panel title="Dimensions">
              <Stack spacing={1.5}>
                {data.dimensions.map((d) => (
                  <Stack key={d.label} spacing={0.5}>
                    <Stack direction="row" justifyContent="space-between"><Typography sx={{ fontSize: 12 }}>{d.label}</Typography><Typography sx={{ ...mono, fontSize: 12 }}>{d.score}%</Typography></Stack>
                    <Meter value={d.score} tone={d.score > 97 ? "ok" : d.score > 93 ? "warn" : "crit"} />
                  </Stack>
                ))}
              </Stack>
            </Panel>
            <DataTable<QualityIssue> rows={data.issues} rowKey={(i) => i.id} columns={[
              { key: "c", header: "Check", render: (i) => <><Typography sx={{ fontSize: 12, fontWeight: 600 }}>{i.check}</Typography><Typography sx={{ fontSize: 11, color: "text.secondary" }}>{i.source}</Typography></> },
              { key: "f", header: "Field", render: (i) => <span style={mono}>{i.field}</span> },
              { key: "n", header: "Failing", align: "right", render: (i) => <span style={mono}>{i.failing.toLocaleString()} / {i.total.toLocaleString()}</span> },
              { key: "s", header: "Severity", render: (i) => <StatusPill label={i.severity} tone={severityTone[i.severity]} /> },
              { key: "a", header: "Action", render: (i) => i.autoFixed
                ? <Typography sx={{ fontSize: 12, color: "success.main", fontWeight: 600 }}>Auto-fixed</Typography>
                : <Stack direction="row" spacing={0.5}>
                    <Button size="small" variant="outlined" onClick={async () => { await api.data.resolveIssue(i.id, "resolve"); toast(`${i.id} resolved`); reload(); }}>Resolve</Button>
                    <Button size="small" onClick={async () => { await api.data.resolveIssue(i.id, "ignore"); toast(`${i.id} ignored`); reload(); }}>Ignore</Button>
                  </Stack> },
            ]} />
          </Box>
        </>
      ) : null}
      {toastNode}
    </Page>
  );
}
