import { Box, Button, Typography } from "@mui/material";
import { api } from "../../api/services";
import { useQuery } from "../../api/useQuery";
import type { LearningSignal } from "../../api/types";
import { Panel, StatusPill } from "../../components/common/Panel";
import { DataTable, KeyValue, Page, StatGrid, mono, useToast } from "../../components/common/Blocks";

const tone = { Accepted: "ok", Rejected: "crit", Overridden: "warn" } as const;

export function LearningPage() {
  const { data, loading } = useQuery(api.ai.learning);
  const { toast, toastNode } = useToast();
  return (
    <Page title="Continuous learning" description="Every analyst accept, reject, and override becomes a labelled example. Hard cases are queued for active learning before the next retrain." loading={loading}>
      {data ? (
        <>
          <StatGrid items={[
            { label: "Labels this week", value: data.stats.labelsThisWeek.toLocaleString() },
            { label: "Accept rate", value: `${data.stats.acceptRate}%`, tone: "ok" },
            { label: "Override rate", value: `${data.stats.overrideRate}%`, tone: "warn" },
            { label: "Active-learning queue", value: String(data.stats.queuedForActiveLearning) },
          ]} />
          <Box sx={{ display: "grid", gridTemplateColumns: { xs: "1fr", lg: "1.6fr 1fr" }, gap: 2.5, alignItems: "start" }}>
            <DataTable<LearningSignal> rows={data.signals} rowKey={(s) => s.id} columns={[
              { key: "t", header: "Time", render: (s) => s.at },
              { key: "m", header: "Match", render: (s) => <span style={mono}>{s.matchId}</span> },
              { key: "a", header: "Analyst", render: (s) => s.analyst },
              { key: "x", header: "Action", render: (s) => <StatusPill label={s.action} tone={tone[s.action]} /> },
              { key: "s", header: "Model score", align: "right", render: (s) => <span style={mono}>{s.modelScore.toFixed(2)}</span> },
              { key: "r", header: "Reason", render: (s) => s.reason },
            ]} />
            <Panel title="Next retrain">
              <KeyValue label="Scheduled" value={data.stats.nextRetrain} />
              <KeyValue label="New labels included" value={data.stats.labelsThisWeek.toLocaleString()} />
              <KeyValue label="Gate" value="Must beat champion on holdout" />
              <KeyValue label="Rollout" value="Shadow 7 days → approval" />
              <Typography sx={{ fontSize: 12, color: "text.secondary", my: 1.5 }}>Disagreements where the model was confident (score ≥ 0.85) but the analyst rejected are weighted higher.</Typography>
              <Button size="small" variant="outlined" onClick={() => toast("Active-learning batch of 50 sent to analyst queue")}>Send hard cases to analysts</Button>
            </Panel>
          </Box>
        </>
      ) : null}
      {toastNode}
    </Page>
  );
}
