import { useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  Box,
  Button,
  Checkbox,
  LinearProgress,
  Snackbar,
  Stack,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableRow,
  Tooltip,
  Typography,
} from "@mui/material";
import { PageHeader } from "../../components/common/PageHeader";
import { StatusPill } from "../../components/common/Panel";
import { ActivityTimeline } from "./ActivityTimeline";
import { approvalHierarchy, approvalKpis, approvals } from "./data";

const materialityTone: Record<string, "ok" | "warn" | "crit"> = {
  High: "crit",
  Medium: "warn",
  Low: "ok",
};

export function ApprovalsPage() {
  const [selectedId, setSelectedId] = useState(approvals[0]?.id);
  const [checked, setChecked] = useState<string[]>([]);
  const [toast, setToast] = useState("");
  const selected = approvals.find((row) => row.id === selectedId) ?? approvals[0];
  const navigate = useNavigate();
  const allChecked = checked.length === approvals.length;

  const toggle = (id: string) => {
    setChecked((current) => (current.includes(id) ? current.filter((item) => item !== id) : [...current, id]));
  };

  const bulk = (action: string) => {
    if (!checked.length) return;
    setToast(`${action} ${checked.length} matches`);
    setChecked([]);
  };

  return (
    <>
      <PageHeader
        title="Approvals"
        description="Controller queue for submitted matches. Approve, reject, or request information with a full audit trail."
        actions={
          <Button variant="outlined" onClick={() => navigate("/exceptions/cases")}>
            Open cases
          </Button>
        }
      />
      <Box sx={{ display: "grid", gridTemplateColumns: { xs: "1fr 1fr", lg: "repeat(4, 1fr)" }, gap: 2 }}>
        {approvalKpis.map((kpi) => (
          <Box key={kpi.label} className="glass" sx={{ p: 1.5, borderRadius: 2 }}>
            <Typography sx={{ fontSize: 11, color: "text.secondary", textTransform: "uppercase" }}>{kpi.label}</Typography>
            <Typography sx={{ fontFamily: '"IBM Plex Sans", sans-serif', fontSize: 20, fontWeight: 700 }}>{kpi.value}</Typography>
          </Box>
        ))}
      </Box>

      <Stack direction="row" spacing={1} flexWrap="wrap">
        <Button size="small" variant="contained" color="success" disabled={!checked.length} onClick={() => bulk("Approved")}>
          Approve selected
        </Button>
        <Button size="small" variant="outlined" color="error" disabled={!checked.length} onClick={() => bulk("Rejected")}>
          Reject selected
        </Button>
        <Button size="small" variant="outlined" disabled={!checked.length} onClick={() => bulk("Requested info on")}>
          Bulk request info
        </Button>
        <Button size="small" variant="text" onClick={() => navigate("/exceptions")}>
          Exception queue
        </Button>
      </Stack>

      <Box sx={{ display: "grid", gridTemplateColumns: { xs: "1fr", lg: "1.5fr 1fr" }, gap: 2.5 }}>
        <Box sx={{ bgcolor: "var(--glass-bg)", backdropFilter: "blur(18px) saturate(150%)", border: "1px solid", borderColor: "divider", borderRadius: 1 }}>
          <Table size="small">
            <TableHead>
              <TableRow>
                <TableCell padding="checkbox">
                  <Checkbox
                    size="small"
                    checked={allChecked}
                    indeterminate={checked.length > 0 && !allChecked}
                    onChange={() => setChecked(allChecked ? [] : approvals.map((row) => row.id))}
                  />
                </TableCell>
                <TableCell>Match ID</TableCell>
                <TableCell>Submitted By</TableCell>
                <TableCell>Entity</TableCell>
                <TableCell>Exposure</TableCell>
                <TableCell>Materiality</TableCell>
                <TableCell>Confidence</TableCell>
                <TableCell>SLA</TableCell>
                <TableCell>Stage</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {approvals.map((row) => (
                <TableRow
                  key={row.id}
                  hover
                  selected={row.id === selected.id}
                  onClick={() => setSelectedId(row.id)}
                  sx={{ cursor: "pointer" }}
                >
                  <TableCell padding="checkbox" onClick={(event) => event.stopPropagation()}>
                    <Checkbox size="small" checked={checked.includes(row.id)} onChange={() => toggle(row.id)} />
                  </TableCell>
                  <TableCell sx={{ fontFamily: '"IBM Plex Sans", sans-serif', fontWeight: 700 }}>
                    {row.id}
                    {row.exceptionOpen ? (
                      <Typography sx={{ fontSize: 10, color: "error.main", fontWeight: 700 }}>Exception linked</Typography>
                    ) : null}
                  </TableCell>
                  <TableCell>{row.submittedBy}</TableCell>
                  <TableCell>{row.entity}</TableCell>
                  <TableCell>{row.exposure}</TableCell>
                  <TableCell>
                    <StatusPill label={row.materiality} tone={materialityTone[row.materiality]} />
                  </TableCell>
                  <TableCell>
                    <Tooltip
                      title={
                        <Stack spacing={0.5}>
                          {row.confidenceFactors.map((factor) => (
                            <Typography key={factor.label} sx={{ fontSize: 12 }}>
                              {factor.label} {factor.weight}%
                            </Typography>
                          ))}
                        </Stack>
                      }
                    >
                      <Typography sx={{ fontSize: 13, fontWeight: 700, textDecoration: "underline dotted" }}>{row.confidence}</Typography>
                    </Tooltip>
                  </TableCell>
                  <TableCell>
                    <StatusPill label={row.sla} tone={row.slaOverdue ? "crit" : "warn"} />
                  </TableCell>
                  <TableCell>{row.stage}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </Box>

        <Box sx={{ p: 2, bgcolor: "var(--glass-bg)", backdropFilter: "blur(18px) saturate(150%)", border: "1px solid", borderColor: "divider", borderRadius: 1 }}>
          <Typography variant="h6">{selected.id}</Typography>
          <Typography sx={{ fontSize: 12, color: "text.secondary", mb: 1.5 }}>
            {selected.entity} · {selected.exposure}
          </Typography>
          <Typography sx={{ fontSize: 12, fontWeight: 700, mb: 0.75 }}>Approval hierarchy</Typography>
          <Stack direction="row" spacing={0.75} alignItems="center" flexWrap="wrap" sx={{ mb: 1.5 }}>
            {approvalHierarchy.map((role, index) => (
              <Stack key={role} direction="row" alignItems="center" spacing={0.75}>
                <Box
                  sx={{
                    px: 1,
                    py: 0.5,
                    borderRadius: 1,
                    fontSize: 11,
                    fontWeight: 800,
                    bgcolor: role === selected.stage ? "primary.main" : "var(--bg-muted)",
                    color: role === selected.stage ? "primary.contrastText" : "text.secondary",
                  }}
                >
                  {role}
                </Box>
                {index < approvalHierarchy.length - 1 ? <Typography sx={{ color: "text.secondary" }}>→</Typography> : null}
              </Stack>
            ))}
          </Stack>
          <Stack direction="row" spacing={1} sx={{ mb: 1.5 }}>
            <StatusPill label={selected.materiality} tone={materialityTone[selected.materiality]} />
            <StatusPill label={selected.sla} tone={selected.slaOverdue ? "crit" : "warn"} />
          </Stack>
          <Typography sx={{ fontSize: 12, fontWeight: 700 }}>Rationale</Typography>
          <Typography sx={{ fontSize: 12, mb: 1.5 }}>{selected.rationale}</Typography>
          <Typography sx={{ fontSize: 12, fontWeight: 700, mb: 0.5 }}>Confidence factors</Typography>
          <Stack spacing={0.6} sx={{ mb: 1.5 }}>
            {selected.confidenceFactors.map((factor) => (
              <Stack key={factor.label} spacing={0.25}>
                <Stack direction="row" justifyContent="space-between">
                  <Typography sx={{ fontSize: 11 }}>{factor.label}</Typography>
                  <Typography sx={{ fontSize: 11, fontWeight: 700 }}>{factor.weight}%</Typography>
                </Stack>
                <LinearProgress variant="determinate" value={factor.weight} sx={{ height: 5, borderRadius: 99 }} />
              </Stack>
            ))}
          </Stack>
          <Typography sx={{ fontSize: 12, fontWeight: 700 }}>Supporting documents</Typography>
          {selected.documents.map((doc) => (
            <Typography key={doc} sx={{ fontSize: 12 }}>
              {doc}
            </Typography>
          ))}
          <Typography sx={{ fontSize: 12, fontWeight: 700, mt: 1.5 }}>Audit trail</Typography>
          {selected.trail.map((item) => (
            <Typography key={item} sx={{ fontSize: 12 }}>
              {item}
            </Typography>
          ))}
          <Stack direction="row" spacing={1} sx={{ mt: 2 }} flexWrap="wrap">
            <Button variant="contained" color="success" onClick={() => navigate("/reconciliation/signoff")}>
              Approve
            </Button>
            <Button variant="outlined" color="error">
              Reject
            </Button>
            <Button variant="outlined">Request information</Button>
            <Button variant="text" onClick={() => navigate("/exceptions/cases")}>
              Open case
            </Button>
          </Stack>
        </Box>
      </Box>
      <ActivityTimeline />
      <Snackbar open={Boolean(toast)} autoHideDuration={2200} onClose={() => setToast("")} message={toast} />
    </>
  );
}
