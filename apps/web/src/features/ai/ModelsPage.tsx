import { Box, Button, Stack, Typography } from "@mui/material";
import { api } from "../../api/services";
import { useQuery } from "../../api/useQuery";
import type { ModelVersion } from "../../api/types";
import { Panel, StatusPill } from "../../components/common/Panel";
import { DataTable, Page, Sparkline, StatGrid, mono, useToast } from "../../components/common/Blocks";

const stageTone = { Production: "ok", Shadow: "warn", Staging: "warn", Archived: "crit" } as const;

export function ModelsPage() {
  const { data, loading } = useQuery(api.ai.models);
  const { toast, toastNode } = useToast();
  const prod = data?.models.find((m) => m.stage === "Production" && m.name === "match-ranker");
  const shadow = data?.models.find((m) => m.stage === "Shadow");
  return (
    <Page title="Models" description="Ranking and similarity models: versions, quality, drift, and controlled promotion from shadow to production." loading={loading}>
      {data && prod && shadow ? (
        <>
          <StatGrid items={[
            { label: "Production precision", value: `${prod.precision}%`, tone: "ok" },
            { label: "Production recall", value: `${prod.recall}%` },
            { label: "Drift (PSI)", value: prod.drift.toFixed(2), tone: prod.drift > 0.1 ? "crit" : "ok", hint: "Alert at 0.10" },
            { label: "Shadow uplift (F1)", value: `+${(shadow.f1 - prod.f1).toFixed(1)} pts`, tone: "ok" },
          ]} />
          <Box sx={{ display: "grid", gridTemplateColumns: { xs: "1fr", md: "1fr 1fr 1fr" }, gap: 2.5 }}>
            <Panel title="Precision · 7 weeks"><Sparkline values={data.trend.precision} /><Typography sx={{ fontSize: 11, color: "text.secondary" }}>{data.trend.weeks[0]} → {data.trend.weeks.at(-1)}</Typography></Panel>
            <Panel title="Drift · 7 weeks"><Sparkline values={data.trend.drift} color="var(--brand-amber)" /><Typography sx={{ fontSize: 11, color: "text.secondary" }}>Population stability index</Typography></Panel>
            <Panel title="Champion vs challenger">
              <Typography sx={{ fontSize: 12, mb: 1 }}>{shadow.name} {shadow.version} beats {prod.version} on precision and recall over 12 days of shadow traffic.</Typography>
              <Button size="small" variant="contained" onClick={() => toast(`Promotion of ${shadow.version} submitted for approval`)}>Request promotion</Button>
            </Panel>
          </Box>
          <DataTable<ModelVersion> rows={data.models} rowKey={(m) => m.name + m.version} columns={[
            { key: "n", header: "Model", render: (m) => <b>{m.name}</b> },
            { key: "v", header: "Version", render: (m) => <span style={mono}>{m.version}</span> },
            { key: "s", header: "Stage", render: (m) => <StatusPill label={m.stage} tone={stageTone[m.stage]} /> },
            { key: "p", header: "Precision", align: "right", render: (m) => `${m.precision}%` },
            { key: "r", header: "Recall", align: "right", render: (m) => `${m.recall}%` },
            { key: "f", header: "F1", align: "right", render: (m) => `${m.f1}%` },
            { key: "d", header: "Drift", align: "right", render: (m) => <Typography sx={{ fontSize: 12, color: m.drift > 0.1 ? "error.main" : "text.primary" }}>{m.drift.toFixed(2)}</Typography> },
            { key: "t", header: "Training data", render: (m) => m.trainedOn },
            { key: "dep", header: "Deployed", render: (m) => m.deployed },
            { key: "a", header: "", render: (m) => <Stack direction="row"><Button size="small" onClick={() => toast(`Model card for ${m.name} ${m.version} opened`)}>Card</Button></Stack> },
          ]} />
        </>
      ) : null}
      {toastNode}
    </Page>
  );
}
