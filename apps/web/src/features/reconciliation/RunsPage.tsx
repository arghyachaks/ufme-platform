import { useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  Box,
  Button,
  MenuItem,
  Select,
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
import { runKpis, runs } from "./data";

const statusTone: Record<string, "ok" | "warn" | "crit"> = {
  Completed: "ok",
  "Signed off": "ok",
  Review: "warn",
  Running: "warn",
};

export function RunsPage() {
  const navigate = useNavigate();
  const [status, setStatus] = useState("All");
  const [entity, setEntity] = useState("All");
  const filtered = useMemo(
    () =>
      runs.filter(
        (run) => (status === "All" || run.status === status) && (entity === "All" || run.entity === entity),
      ),
    [status, entity],
  );

  return (
    <>
      <PageHeader
        title="Reconciliation Runs"
        description="Create and execute jobs, then open a run to review matches without leaving this module."
      />
      <ReconRecoBar />
      <Box sx={{ display: "grid", gridTemplateColumns: { xs: "1fr 1fr", lg: "repeat(5, 1fr)" }, gap: 2 }}>
        {runKpis.map((kpi) => (
          <Box key={kpi.label} sx={{ p: 1.5, bgcolor: "background.paper", border: "1px solid", borderColor: "divider", borderRadius: 1 }}>
            <Typography sx={{ fontSize: 11, color: "text.secondary", textTransform: "uppercase" }}>{kpi.label}</Typography>
            <Typography sx={{ fontFamily: '"IBM Plex Sans", sans-serif', fontSize: 20, fontWeight: 700 }}>{kpi.value}</Typography>
          </Box>
        ))}
      </Box>

      <Stack direction="row" spacing={1} flexWrap="wrap">
        <Select size="small" value={status} onChange={(event) => setStatus(event.target.value)}>
          {["All", "Running", "Review", "Completed", "Signed off"].map((item) => (
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
      </Stack>

      <Box sx={{ bgcolor: "background.paper", border: "1px solid", borderColor: "divider", borderRadius: 1 }}>
        <Table size="small">
          <TableHead>
            <TableRow>
              <TableCell>Run ID</TableCell>
              <TableCell>Type</TableCell>
              <TableCell>Entity</TableCell>
              <TableCell>Period</TableCell>
              <TableCell>Status</TableCell>
              <TableCell>Match Rate</TableCell>
              <TableCell>Exposure</TableCell>
              <TableCell>Start</TableCell>
              <TableCell>Duration</TableCell>
              <TableCell>Actions</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {filtered.map((run) => (
              <TableRow key={run.id} hover>
                <TableCell sx={{ fontFamily: '"IBM Plex Sans", sans-serif', fontWeight: 700 }}>{run.id}</TableCell>
                <TableCell>{run.type}</TableCell>
                <TableCell>{run.entity}</TableCell>
                <TableCell>{run.period}</TableCell>
                <TableCell>
                  <StatusPill label={run.status} tone={statusTone[run.status] ?? "warn"} />
                </TableCell>
                <TableCell>{run.matchRate}</TableCell>
                <TableCell>{run.exposure}</TableCell>
                <TableCell>{run.start}</TableCell>
                <TableCell>{run.duration}</TableCell>
                <TableCell>
                  <Stack direction="row" spacing={0.5}>
                    <Button size="small" onClick={() => navigate(`/reconciliation/review?run=${run.id}`)}>
                      Open
                    </Button>
                    <Button size="small">Rerun</Button>
                    <Button size="small">Download</Button>
                    <Button size="small">Compare</Button>
                  </Stack>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </Box>
      <ActivityTimeline />
    </>
  );
}
