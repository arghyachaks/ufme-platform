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
  Divider,
  Drawer,
  IconButton,
  LinearProgress,
  ListItemText,
  Menu,
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
import MoreVertIcon from "@mui/icons-material/MoreVert";
import { PageHeader } from "../../components/common/PageHeader";
import { StatusPill } from "../../components/common/Panel";
import { ActivityTimeline } from "./ActivityTimeline";
import { ReconRecoBar } from "./ReconLayout";
import { workspaceApi, type ReconData } from "../../api/services";
import { useQuery } from "../../api/useQuery";
import { PageSkeleton } from "../../components/common/Blocks";

type Run = (ReconData["runs"])[number];

const statusTone: Record<string, "ok" | "warn" | "crit"> = {
  Completed: "ok",
  "Signed off": "ok",
  "Review Required": "warn",
  Review: "warn",
  Running: "warn",
  Failed: "crit",
};

const materialityTone: Record<string, "ok" | "warn" | "crit"> = {
  High: "crit",
  Medium: "warn",
  Low: "ok",
};

export function RunsPage() {
  const { data } = useQuery(workspaceApi.recon);
  return data ? <RunsPageView d={data} /> : <PageSkeleton />;
}

function RunsPageView({ d }: { d: ReconData }) {
  const { reconActivity, runKpis, runTrends, runs, trendDays } = d;
  const navigate = useNavigate();
  const [status, setStatus] = useState("All");
  const [entity, setEntity] = useState("All");
  const [selected, setSelected] = useState<string[]>([]);
  const [compareOpen, setCompareOpen] = useState(false);
  const [trendKey, setTrendKey] = useState<"matchRate" | "exposure" | "exceptions" | null>(null);
  const [detailRun, setDetailRun] = useState<Run | null>(null);
  const [auditRun, setAuditRun] = useState<Run | null>(null);
  const [toast, setToast] = useState("");
  const [actionMenu, setActionMenu] = useState<{ anchor: HTMLElement; run: Run } | null>(null);

  const filtered = useMemo(() => {
    const rows = runs.filter(
      (run) => (status === "All" || run.status === status) && (entity === "All" || run.entity === entity),
    );
    return [...rows].sort((a, b) => b.exposureValue - a.exposureValue);
  }, [status, entity]);

  const compareRows = runs.filter((run) => selected.includes(run.id));
  const allSelected = filtered.length > 0 && filtered.every((run) => selected.includes(run.id));

  const toggle = (id: string) => {
    setSelected((current) => (current.includes(id) ? current.filter((item) => item !== id) : [...current, id]));
  };

  const bulk = (action: string) => {
    if (!selected.length) return;
    setToast(`${action} ${selected.length} runs`);
    if (action === "Archived") setSelected([]);
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
          <Box key={kpi.label} className="glass" sx={{ p: 1.5, borderRadius: 2 }}>
            <Typography sx={{ fontSize: 11, color: "text.secondary", textTransform: "uppercase" }}>{kpi.label}</Typography>
            <Typography sx={{ fontFamily: 'var(--font-mono)', fontSize: 20, fontWeight: 700 }}>{kpi.value}</Typography>
          </Box>
        ))}
      </Box>

      <Box sx={{ display: "grid", gridTemplateColumns: { xs: "1fr", md: "repeat(3, 1fr)" }, gap: 2 }}>
        <TrendCard title="7-day match rate" unit="%" values={runTrends.matchRate} onOpen={() => setTrendKey("matchRate")} />
        <TrendCard title="7-day exposure" unit="M" prefix="$" values={runTrends.exposure} onOpen={() => setTrendKey("exposure")} />
        <TrendCard title="7-day exceptions" unit="k" values={runTrends.exceptions} onOpen={() => setTrendKey("exceptions")} />
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
        <Button size="small" variant="outlined" disabled={!selected.length} onClick={() => bulk("Reran")}>
          Bulk rerun
        </Button>
        <Button size="small" variant="outlined" disabled={!selected.length} onClick={() => bulk("Exported")}>
          Bulk export
        </Button>
        <Button size="small" variant="outlined" disabled={!selected.length} onClick={() => bulk("Archived")}>
          Bulk archive
        </Button>
      </Stack>

      <Box sx={{ bgcolor: "var(--glass-bg)", border: "1px solid", borderColor: "var(--glass-border)", borderRadius: "2px", overflow: "auto" }}>
        <Table size="small">
          <TableHead>
            <TableRow>
              <TableCell padding="checkbox">
                <Checkbox
                  size="small"
                  checked={allSelected}
                  indeterminate={selected.length > 0 && !allSelected}
                  onChange={() => setSelected(allSelected ? [] : filtered.map((run) => run.id))}
                />
              </TableCell>
              <TableCell>Run ID</TableCell>
              <TableCell>Type</TableCell>
              <TableCell>Entity</TableCell>
              <TableCell>Period</TableCell>
              <TableCell>Status</TableCell>
              <TableCell>Match Rate</TableCell>
              <TableCell>Exposure</TableCell>
              <TableCell>Materiality</TableCell>
              <TableCell>Rule / Model</TableCell>
              <TableCell>Start</TableCell>
              <TableCell>Duration</TableCell>
              <TableCell align="right" sx={{ whiteSpace: "nowrap", width: 148 }}>
                Actions
              </TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {filtered.map((run) => (
              <TableRow key={run.id} hover>
                <TableCell padding="checkbox">
                  <Checkbox size="small" checked={selected.includes(run.id)} onChange={() => toggle(run.id)} />
                </TableCell>
                <TableCell>
                  <Button size="small" sx={{ px: 0, fontFamily: 'var(--font-mono)', fontWeight: 700 }} onClick={() => setDetailRun(run)}>
                    {run.id}
                  </Button>
                </TableCell>
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
                  <StatusPill label={run.materiality} tone={materialityTone[run.materiality]} />
                </TableCell>
                <TableCell>
                  <Typography sx={{ fontSize: 11 }}>{run.ruleVersion}</Typography>
                  <Typography sx={{ fontSize: 11, color: "text.secondary" }}>{run.modelVersion}</Typography>
                </TableCell>
                <TableCell>{run.start}</TableCell>
                <TableCell>{run.duration}</TableCell>
                <TableCell align="right" sx={{ whiteSpace: "nowrap" }}>
                  <Stack direction="row" spacing={0.75} justifyContent="flex-end" alignItems="center">
                    <Button
                      size="small"
                      variant="contained"
                      onClick={() => navigate(`/reconciliation/review?run=${run.id}`)}
                    >
                      Open
                    </Button>
                    <IconButton
                      size="small"
                      aria-label={`More actions for ${run.id}`}
                      onClick={(event) => setActionMenu({ anchor: event.currentTarget, run })}
                      sx={{
                        border: "1px solid",
                        borderColor: "var(--glass-border)",
                        bgcolor: "var(--glass-bg)",
                        backdropFilter: "blur(12px)",
                      }}
                    >
                      <MoreVertIcon fontSize="small" />
                    </IconButton>
                  </Stack>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </Box>
      <ActivityTimeline />

      <Drawer anchor="right" open={Boolean(detailRun)} onClose={() => setDetailRun(null)}>
        <Box sx={{ width: { xs: 320, sm: 420 }, p: 2.5 }}>
          <Typography variant="h6" sx={{ mb: 0.5 }}>
            Run summary
          </Typography>
          <Typography sx={{ fontSize: 13, fontWeight: 700, mb: 2 }}>{detailRun?.id}</Typography>
          <Detail label="Data source" value={detailRun?.dataSource} />
          <Detail label="Transactions processed" value={detailRun?.transactionsProcessed} />
          <Detail label="Rules executed" value={detailRun?.rulesExecuted.join(", ")} />
          <Detail label="Matching model" value={detailRun?.modelVersion} />
          <Detail label="Rule version" value={detailRun?.ruleVersion} />
          <Detail label="Exception summary" value={detailRun?.exceptionSummary} />
          <Typography sx={{ fontSize: 12, fontWeight: 700, mt: 2, mb: 1 }}>Runtime breakdown</Typography>
          {detailRun?.runtimeBreakdown.map((item) => (
            <Detail key={item.step} label={item.step} value={item.time} />
          ))}
          <Button sx={{ mt: 2 }} variant="contained" onClick={() => detailRun && navigate(`/reconciliation/review?run=${detailRun.id}`)}>
            Open review
          </Button>
        </Box>
      </Drawer>

      <Dialog open={Boolean(trendKey)} onClose={() => setTrendKey(null)} maxWidth="sm" fullWidth>
        <DialogTitle>Trend analytics</DialogTitle>
        <DialogContent>
          <Table size="small">
            <TableHead>
              <TableRow>
                <TableCell>Day</TableCell>
                <TableCell>{trendKey === "matchRate" ? "Match rate %" : trendKey === "exposure" ? "Exposure $M" : "Exceptions k"}</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {trendKey &&
                runTrends[trendKey].map((value, index) => (
                  <TableRow key={trendDays[index]}>
                    <TableCell>{trendDays[index]}</TableCell>
                    <TableCell sx={{ fontFamily: 'var(--font-mono)', fontWeight: 700 }}>{value}</TableCell>
                  </TableRow>
                ))}
            </TableBody>
          </Table>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setTrendKey(null)}>Close</Button>
        </DialogActions>
      </Dialog>

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
                ["Entity", (run: Run) => run.entity],
                ["Status", (run: Run) => run.status],
                ["Match rate", (run: Run) => run.matchRate],
                ["Exposure", (run: Run) => run.exposure],
                ["Materiality", (run: Run) => run.materiality],
                ["Rule version", (run: Run) => run.ruleVersion],
                ["Matching model", (run: Run) => run.modelVersion],
                ["Duration", (run: Run) => run.duration],
              ].map(([label, getter]) => (
                <TableRow key={String(label)}>
                  <TableCell sx={{ fontWeight: 700 }}>{label as string}</TableCell>
                  {compareRows.map((run) => (
                    <TableCell key={run.id}>{(getter as (run: Run) => string)(run)}</TableCell>
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

      <Menu
        anchorEl={actionMenu?.anchor}
        open={Boolean(actionMenu)}
        onClose={() => setActionMenu(null)}
        anchorOrigin={{ vertical: "bottom", horizontal: "right" }}
        transformOrigin={{ vertical: "top", horizontal: "right" }}
        slotProps={{ paper: { sx: { minWidth: 220, mt: 0.5 } } }}
      >
        <MenuItem
          onClick={() => {
            setToast(`Reran ${actionMenu?.run.id}`);
            setActionMenu(null);
          }}
        >
          <ListItemText primary="Rerun" secondary="Re-execute with the same rules" />
        </MenuItem>
        <MenuItem
          onClick={() => {
            setToast(`Cloned ${actionMenu?.run.id}`);
            setActionMenu(null);
          }}
        >
          <ListItemText primary="Clone" secondary="Copy configuration to a new run" />
        </MenuItem>
        <Divider />
        <MenuItem
          onClick={() => {
            setActionMenu(null);
            navigate("/exceptions/cases");
          }}
        >
          <ListItemText primary="Create exception case" secondary="Escalate unmatched exposure" />
        </MenuItem>
        <MenuItem
          onClick={() => {
            if (actionMenu) setAuditRun(actionMenu.run);
            setActionMenu(null);
          }}
        >
          <ListItemText primary="View audit trail" secondary="Rule, model, and activity log" />
        </MenuItem>
        <Divider />
        <MenuItem
          onClick={() => {
            setToast(`Download queued for ${actionMenu?.run.id}`);
            setActionMenu(null);
          }}
        >
          <ListItemText primary="Download pack" secondary="Evidence export for controllers" />
        </MenuItem>
      </Menu>

      <Snackbar open={Boolean(toast)} autoHideDuration={2500} onClose={() => setToast("")} message={toast} />
    </>
  );
}

function Detail({ label, value }: { label: string; value?: string }) {
  return (
    <Stack direction="row" justifyContent="space-between" gap={2} sx={{ py: 0.75, borderBottom: "1px solid", borderColor: "divider" }}>
      <Typography sx={{ fontSize: 12, color: "text.secondary" }}>{label}</Typography>
      <Typography sx={{ fontSize: 12, fontWeight: 700, textAlign: "right" }}>{value}</Typography>
    </Stack>
  );
}

function TrendCard({
  title,
  values,
  unit,
  prefix = "",
  onOpen,
}: {
  title: string;
  values: number[];
  unit: string;
  prefix?: string;
  onOpen: () => void;
}) {
  const latest = values[values.length - 1];
  const previous = values[values.length - 2];
  const delta = latest - previous;
  const max = Math.max(...values);
  const min = Math.min(...values);
  return (
    <Box
      role="button"
      tabIndex={0}
      onClick={onOpen}
      onKeyDown={(event) => {
        if (event.key === "Enter" || event.key === " ") onOpen();
      }}
      sx={{
        p: 2,
        bgcolor: "var(--glass-bg)",         border: "1px solid",
        borderColor: "divider",
        borderRadius: 1,
        cursor: "pointer",
        "&:hover": { borderColor: "primary.main" },
      }}
    >
      <Typography sx={{ fontSize: 11, color: "text.secondary", textTransform: "uppercase" }}>{title}</Typography>
      <Typography sx={{ fontSize: 11, color: "primary.main", fontWeight: 700 }}>Open analytics</Typography>
      <Stack direction="row" justifyContent="space-between" alignItems="flex-end" sx={{ mt: 1 }}>
        <Box>
          <Typography sx={{ fontFamily: 'var(--font-mono)', fontSize: 22, fontWeight: 700 }}>
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
