import { useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  Box,
  Button,
  Checkbox,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  LinearProgress,
  MenuItem,
  Select,
  Snackbar,
  Stack,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableRow,
  Typography,
} from "@mui/material";
import { PageHeader } from "../../components/common/PageHeader";
import { StatusPill } from "../../components/common/Panel";
import { ActivityTimeline } from "./ActivityTimeline";
import { ReconRecoBar } from "./ReconLayout";
import { reconActivity, runKpis, runTrends, runs } from "./data";

const statusTone: Record<string, "ok" | "warn" | "crit"> = {
  Completed: "ok",
  "Signed off": "ok",
  "Review Required": "warn",
  Review: "warn",
  Running: "warn",
  Failed: "crit",
};

export function RunsPage() {
  const navigate = useNavigate();
  const [status, setStatus] = useState("All");
  const [entity, setEntity] = useState("All");
  const [selected, setSelected] = useState<string[]>([]);
  const [compareOpen, setCompareOpen] = useState(false);
  const [auditRun, setAuditRun] = useState<(typeof runs)[number] | null>(null);
  const [toast, setToast] = useState("");

  const filtered = useMemo(() => {
    const rows = runs.filter(
      (run) => (status === "All" || run.status === status) && (entity === "All" || run.entity === entity),
    );
    return [...rows].sort((a, b) => b.exposureValue - a.exposureValue);
  }, [status, entity]);

  const compareRows = runs.filter((run) => selected.includes(run.id));

  const toggle = (id: string) => {
    setSelected((current) => (current.includes(id) ? current.filter((item) => item !== id) : [...current, id]));
  };

  return (
    <>
      <PageHeader
        title="Reconciliation Runs"
        description="Create and execute jobs, then open a run to review matches without leaving this module. Default sort is financial exposure, highest first."
      />
      <ReconRecoBar />
      <Box sx={{ display: "grid", gridTemplateColumns: { xs: "1fr 1fr", lg: "repeat(7, 1fr)" }, gap: 2 }}>
        {runKpis.map((kpi) => (
          <Box key={kpi.label} sx={{ p: 1.5, bgcolor: "background.paper", border: "1px solid", borderColor: "divider", borderRadius: 1 }}>
            <Typography sx={{ fontSize: 11, color: "text.secondary", textTransform: "uppercase" }}>{kpi.label}</Typography>
            <Typography sx={{ fontFamily: '"IBM Plex Sans", sans-serif', fontSize: 20, fontWeight: 700 }}>{kpi.value}</Typography>
          </Box>
        ))}
      </Box>

      <Box sx={{ display: "grid", gridTemplateColumns: { xs: "1fr", md: "repeat(3, 1fr)" }, gap: 2 }}>
        <TrendCard title="7-day match rate" unit="%" values={runTrends.matchRate} />
        <TrendCard title="7-day exposure" unit="M" prefix="$" values={runTrends.exposure} />
        <TrendCard title="7-day exceptions" unit="k" values={runTrends.exceptions} />
      </Box>

      <Stack direction="row" spacing={1} flexWrap="wrap" alignItems="center">
        <Select size="small" value={status} onChange={(event) => setStatus(event.target.value)}>
          {["All", "Running", "Review Required", "Completed", "Failed"].map((item) => (
            <MenuItem key={item} value={item}>
              {item}
            </MenuItem>
          ))}
        </Select>
        <Select size="small" value={entity} onChange={(event) => setEntity(event.target.value)}>
          {["All", "APAC", "EMEA", "NAMER"].map((item) => (
            <MenuItem key={item} value={item}>
              {item}
            </MenuItem>
          ))}
        </Select>
        <Button size="small" variant="outlined" disabled={selected.length < 2} onClick={() => setCompareOpen(true)}>
          Compare selected ({selected.length})
        </Button>
      </Stack>

      <Box sx={{ bgcolor: "background.paper", border: "1px solid", borderColor: "divider", borderRadius: 1, overflow: "auto" }}>
        <Table size="small">
          <TableHead>
            <TableRow>
              <TableCell padding="checkbox" />
              <TableCell>Run ID</TableCell>
              <TableCell>Type</TableCell>
              <TableCell>Entity</TableCell>
              <TableCell>Period</TableCell>
              <TableCell>Status</TableCell>
              <TableCell>Match Rate</TableCell>
              <TableCell>Exposure</TableCell>
              <TableCell>Rule / Model</TableCell>
              <TableCell>Start</TableCell>
              <TableCell>Duration</TableCell>
              <TableCell>Actions</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {filtered.map((run) => (
              <TableRow key={run.id} hover>
                <TableCell padding="checkbox">
                  <Checkbox size="small" checked={selected.includes(run.id)} onChange={() => toggle(run.id)} />
                </TableCell>
                <TableCell sx={{ fontFamily: '"IBM Plex Sans", sans-serif', fontWeight: 700 }}>{run.id}</TableCell>
                <TableCell>{run.type}</TableCell>
                <TableCell>{run.entity}</TableCell>
                <TableCell>{run.period}</TableCell>
                <TableCell sx={{ minWidth: 160 }}>
                  <Stack spacing={0.75}>
                    <StatusPill label={run.status} tone={statusTone[run.status] ?? "warn"} />
                    <LinearProgress
                      variant="determinate"
                      value={run.progress}
                      color={run.status === "Failed" ? "error" : run.status === "Completed" ? "success" : "primary"}
                      sx={{ height: 6, borderRadius: 99 }}
                    />
                  </Stack>
                </TableCell>
                <TableCell>{run.matchRate}</TableCell>
                <TableCell sx={{ fontWeight: 700 }}>{run.exposure}</TableCell>
                <TableCell>
                  <Typography sx={{ fontSize: 11 }}>{run.ruleVersion}</Typography>
                  <Typography sx={{ fontSize: 11, color: "text.secondary" }}>{run.modelVersion}</Typography>
                </TableCell>
                <TableCell>{run.start}</TableCell>
                <TableCell>{run.duration}</TableCell>
                <TableCell>
                  <Stack direction="row" spacing={0.5} flexWrap="wrap" sx={{ maxWidth: 420 }}>
                    <Button size="small" onClick={() => navigate(`/reconciliation/review?run=${run.id}`)}>
                      Open
                    </Button>
                    <Button size="small">Rerun</Button>
                    <Button size="small" onClick={() => setToast(`Cloned ${run.id}`)}>
                      Clone
                    </Button>
                    <Button size="small" onClick={() => navigate("/exceptions/cases")}>
                      Exception case
                    </Button>
                    <Button size="small" onClick={() => setAuditRun(run)}>
                      Audit trail
                    </Button>
                    <Button size="small">Download</Button>
                  </Stack>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </Box>
      <ActivityTimeline />

      <Dialog open={compareOpen} onClose={() => setCompareOpen(false)} maxWidth="md" fullWidth>
        <DialogTitle>Run comparison</DialogTitle>
        <DialogContent>
          <Table size="small">
            <TableHead>
              <TableRow>
                <TableCell>Field</TableCell>
                {compareRows.map((run) => (
                  <TableCell key={run.id}>{run.id}</TableCell>
                ))}
              </TableRow>
            </TableHead>
            <TableBody>
              {[
                ["Entity", (run: (typeof runs)[number]) => run.entity],
                ["Status", (run: (typeof runs)[number]) => run.status],
                ["Match rate", (run: (typeof runs)[number]) => run.matchRate],
                ["Exposure", (run: (typeof runs)[number]) => run.exposure],
                ["Rule version", (run: (typeof runs)[number]) => run.ruleVersion],
                ["AI model", (run: (typeof runs)[number]) => run.modelVersion],
                ["Duration", (run: (typeof runs)[number]) => run.duration],
              ].map(([label, getter]) => (
                <TableRow key={String(label)}>
                  <TableCell sx={{ fontWeight: 700 }}>{label as string}</TableCell>
                  {compareRows.map((run) => (
                    <TableCell key={run.id}>{(getter as (run: (typeof runs)[number]) => string)(run)}</TableCell>
                  ))}
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setCompareOpen(false)}>Close</Button>
        </DialogActions>
      </Dialog>

      <Dialog open={Boolean(auditRun)} onClose={() => setAuditRun(null)} maxWidth="sm" fullWidth>
        <DialogTitle>Audit trail · {auditRun?.id}</DialogTitle>
        <DialogContent>
          <Typography sx={{ fontSize: 12, mb: 1.5 }}>
            Rule {auditRun?.ruleVersion} · Model {auditRun?.modelVersion}
          </Typography>
          <Stack spacing={1}>
            {reconActivity.map((item) => (
              <Typography key={`${item.time}-${item.text}`} sx={{ fontSize: 12 }}>
                {item.time} · {item.actor} · {item.text}
              </Typography>
            ))}
          </Stack>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setAuditRun(null)}>Close</Button>
        </DialogActions>
      </Dialog>

      <Snackbar open={Boolean(toast)} autoHideDuration={2500} onClose={() => setToast("")} message={toast} />
    </>
  );
}

function TrendCard({
  title,
  values,
  unit,
  prefix = "",
}: {
  title: string;
  values: number[];
  unit: string;
  prefix?: string;
}) {
  const latest = values[values.length - 1];
  const previous = values[values.length - 2];
  const delta = latest - previous;
  const max = Math.max(...values);
  const min = Math.min(...values);
  return (
    <Box sx={{ p: 2, bgcolor: "background.paper", border: "1px solid", borderColor: "divider", borderRadius: 1 }}>
      <Typography sx={{ fontSize: 11, color: "text.secondary", textTransform: "uppercase" }}>{title}</Typography>
      <Stack direction="row" justifyContent="space-between" alignItems="flex-end" sx={{ mt: 1 }}>
        <Box>
          <Typography sx={{ fontFamily: '"IBM Plex Sans", sans-serif', fontSize: 22, fontWeight: 700 }}>
            {prefix}
            {latest}
            {unit}
          </Typography>
          <Typography sx={{ fontSize: 12, color: delta <= 0 && title.includes("match") ? "error.main" : "success.main" }}>
            {delta > 0 ? "+" : ""}
            {delta.toFixed(1)} vs prior day
          </Typography>
        </Box>
        <Stack direction="row" alignItems="flex-end" spacing={0.4} sx={{ height: 40 }}>
          {values.map((value, index) => (
            <Box
              key={`${title}-${index}`}
              sx={{
                width: 10,
                height: `${12 + ((value - min) / (max - min || 1)) * 28}px`,
                bgcolor: index === values.length - 1 ? "primary.main" : "divider",
                borderRadius: 0.5,
              }}
            />
          ))}
        </Stack>
      </Stack>
    </Box>
  );
}
