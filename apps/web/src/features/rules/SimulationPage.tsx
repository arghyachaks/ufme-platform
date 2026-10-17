import { useState } from "react";
import { Box, Button, LinearProgress, MenuItem, Stack, TextField, Typography } from "@mui/material";
import { api } from "../../api/services";
import { useQuery } from "../../api/useQuery";
import type { SimulationResult } from "../../api/types";
import { Panel } from "../../components/common/Panel";
import { Page, StatGrid, money, mono, useToast } from "../../components/common/Blocks";

export function SimulationPage() {
  const { data: scenarios = [], loading } = useQuery(api.simulation.scenarios);
  const [scenario, setScenario] = useState("widen");
  const [dataset, setDataset] = useState("July 2026 IC actuals");
  const [running, setRunning] = useState(false);
  const [result, setResult] = useState<SimulationResult | null>(null);
  const { toast, toastNode } = useToast();

  const run = async () => {
    setRunning(true);
    setResult(null);
    setResult(await api.simulation.run(scenario));
    setRunning(false);
  };
  const delta = result ? result.matchRate - result.baselineMatchRate : 0;

  return (
    <Page title="Rule simulation" description="Replay draft rules and policy changes against historical or synthetic data before publishing. Nothing here affects production matches." loading={loading}>
      <Panel title="Scenario">
        <Stack direction={{ xs: "column", md: "row" }} spacing={2} alignItems={{ md: "center" }}>
          <TextField select size="small" label="Change to test" value={scenario} onChange={(e) => setScenario(e.target.value)} sx={{ minWidth: 260 }}>
            {scenarios.map((s) => <MenuItem key={s.key} value={s.key}>{s.label}</MenuItem>)}
          </TextField>
          <TextField select size="small" label="Dataset" value={dataset} onChange={(e) => setDataset(e.target.value)} sx={{ minWidth: 220 }}>
            {["July 2026 IC actuals", "Q2 2026 IC actuals", "Synthetic payroll Q2", "Synthetic stress (5M rows)"].map((d) => <MenuItem key={d} value={d}>{d}</MenuItem>)}
          </TextField>
          <Button variant="contained" onClick={run} disabled={running}>{running ? "Running…" : "Run simulation"}</Button>
        </Stack>
        {running ? <LinearProgress sx={{ mt: 2 }} /> : null}
      </Panel>

      {result ? (
        <>
          <StatGrid items={[
            { label: "Match rate", value: `${result.matchRate}%`, hint: `Baseline ${result.baselineMatchRate}%`, tone: delta > 0 ? "ok" : undefined },
            { label: "Δ match rate", value: `${delta >= 0 ? "+" : ""}${delta.toFixed(1)} pts`, tone: delta > 0 ? "ok" : "warn" },
            { label: "New matches", value: result.newMatches.toLocaleString(), tone: "ok" },
            { label: "False positives", value: String(result.falsePositives), tone: result.falsePositives > 20 ? "crit" : "ok", hint: "Vs labelled truth" },
            { label: "Exposure cleared", value: money(result.exposureCleared) },
          ]} />
          <Box sx={{ display: "grid", gridTemplateColumns: { xs: "1fr", md: "1fr 1fr" }, gap: 2.5 }}>
            <Panel title="Baseline vs scenario">
              {[["Baseline", result.baselineMatchRate], ["Scenario", result.matchRate]].map(([label, v]) => (
                <Stack key={label} direction="row" spacing={1.5} alignItems="center" sx={{ mb: 1.5 }}>
                  <Typography sx={{ fontSize: 12, width: 70 }}>{label}</Typography>
                  <Box sx={{ flex: 1, height: 22, borderRadius: 1, bgcolor: "var(--bg-muted)", overflow: "hidden" }}>
                    <Box sx={{ width: `${v}%`, height: "100%", bgcolor: label === "Scenario" ? "primary.main" : "text.secondary", opacity: label === "Scenario" ? 0.85 : 0.35, transition: "width 0.8s" }} />
                  </Box>
                  <Typography sx={{ ...mono, fontSize: 12, width: 48 }}>{v}%</Typography>
                </Stack>
              ))}
              <Typography sx={{ fontSize: 12, color: "text.secondary" }}>{result.lostMatches} previously matched pairs would no longer match.</Typography>
            </Panel>
            <Panel title="Recommendation">
              <Typography sx={{ fontSize: 13, mb: 2 }}>
                {result.falsePositives > 20
                  ? "Gain is real but false positives rise sharply. Consider limiting the wider tolerance to exposures below 50K or requiring analyst review."
                  : "Change improves coverage with acceptable precision. Safe to submit for controller approval."}
              </Typography>
              <Stack direction="row" spacing={1}>
                <Button size="small" variant="outlined" onClick={() => toast("Sample of changed matches exported")}>Export diff</Button>
                <Button size="small" variant="contained" onClick={() => toast("Change submitted for publish approval with simulation evidence")}>Submit for publish</Button>
              </Stack>
            </Panel>
          </Box>
        </>
      ) : !running ? (
        <Typography sx={{ color: "text.secondary", fontSize: 13 }}>Pick a change and dataset, then run the simulation to see its impact.</Typography>
      ) : null}
      {toastNode}
    </Page>
  );
}
