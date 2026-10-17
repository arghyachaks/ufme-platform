import { useState } from "react";
import { Box, Chip, Stack, ToggleButton, ToggleButtonGroup, Typography } from "@mui/material";
import { api } from "../../api/services";
import { useQuery } from "../../api/useQuery";
import { Panel } from "../../components/common/Panel";
import { Page, StatGrid, mono } from "../../components/common/Blocks";

export function ExplainabilityPage() {
  const { data = [], loading } = useQuery(api.ai.explanations);
  const [id, setId] = useState<string>();
  const ex = data.find((e) => e.matchId === id) ?? data[0];
  const max = ex ? Math.max(...ex.contributions.map((c) => Math.abs(c.weight))) : 1;

  return (
    <Page title="Explainability" description="Why a match was proposed or rejected: rules fired, feature contributions, and what would change the decision." loading={loading}
      actions={ex ? (
        <ToggleButtonGroup size="small" exclusive value={ex.matchId} onChange={(_, v) => v && setId(v)}>
          {data.map((e) => <ToggleButton key={e.matchId} value={e.matchId}>{e.matchId}</ToggleButton>)}
        </ToggleButtonGroup>
      ) : undefined}>
      {ex ? (
        <>
          <StatGrid items={[
            { label: "Confidence", value: ex.confidence.toFixed(2), tone: ex.confidence >= 0.8 ? "ok" : "warn" },
            { label: "Decision", value: ex.confidence >= 0.97 ? "Auto" : ex.confidence >= 0.8 ? "Review" : "Exception" },
            { label: "Rules fired", value: String(ex.rulesFired.length) },
            { label: "Model", value: "ranker 2.4.1" },
          ]} />
          <Box sx={{ display: "grid", gridTemplateColumns: { xs: "1fr", lg: "1.4fr 1fr" }, gap: 2.5 }}>
            <Panel title="Feature contributions">
              <Stack spacing={1.25}>
                {ex.contributions.map((c) => {
                  const pos = c.weight >= 0;
                  const w = (Math.abs(c.weight) / max) * 50;
                  return (
                    <Stack key={c.feature} direction="row" alignItems="center" spacing={1}>
                      <Box sx={{ width: 170 }}>
                        <Typography sx={{ fontSize: 12, fontWeight: 600 }}>{c.feature}</Typography>
                        <Typography sx={{ fontSize: 11, color: "text.secondary" }}>{c.value}</Typography>
                      </Box>
                      <Box sx={{ flex: 1, position: "relative", height: 16 }}>
                        <Box sx={{ position: "absolute", left: "50%", top: 0, bottom: 0, width: "1px", bgcolor: "divider" }} />
                        <Box sx={{ position: "absolute", top: 2, height: 12, borderRadius: 1, bgcolor: pos ? "success.main" : "error.main", opacity: 0.75,
                          left: pos ? "50%" : `${50 - w}%`, width: `${w}%` }} />
                      </Box>
                      <Typography sx={{ ...mono, fontSize: 12, width: 48, textAlign: "right", color: pos ? "success.main" : "error.main" }}>{pos ? "+" : ""}{c.weight.toFixed(2)}</Typography>
                    </Stack>
                  );
                })}
              </Stack>
            </Panel>
            <Stack spacing={2.5}>
              <Panel title="Decision">
                <Typography sx={{ fontSize: 13, mb: 1.5 }}>{ex.decision}</Typography>
                <Typography variant="subtitle2" sx={{ mb: 0.75 }}>Rules fired</Typography>
                <Stack direction="row" spacing={0.5} flexWrap="wrap" useFlexGap>{ex.rulesFired.map((r) => <Chip key={r} size="small" label={r} />)}</Stack>
              </Panel>
              <Panel title="What would change it">
                <Typography sx={{ fontSize: 13 }}>{ex.counterfactual}</Typography>
              </Panel>
            </Stack>
          </Box>
        </>
      ) : null}
    </Page>
  );
}
