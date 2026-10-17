import { useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  Box,
  Button,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  Stack,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableRow,
  TextField,
  Typography,
} from "@mui/material";
import { PageHeader } from "../../components/common/PageHeader";
import { StatusPill } from "../../components/common/Panel";
import { ActivityTimeline } from "./ActivityTimeline";
import { workspaceApi, type ReconData } from "../../api/services";
import { useQuery } from "../../api/useQuery";
import { PageSkeleton } from "../../components/common/Blocks";

const statusTone: Record<string, "ok" | "warn" | "crit"> = {
  "Signed off": "ok",
  "Manager signed": "warn",
  "Pending controller": "crit",
};

export function SignoffPage() {
  const { data } = useQuery(workspaceApi.recon);
  return data ? <SignoffPageView d={data} /> : <PageSkeleton />;
}

function SignoffPageView({ d }: { d: ReconData }) {
  const { closeReadiness, failedControls, signoffChecklist, signoffEntities, signoffEvidence, signoffExceptionSummary, signoffFlow } = d;
  const navigate = useNavigate();
  const [comment, setComment] = useState("");
  const [controlOpen, setControlOpen] = useState(false);
  const failed = failedControls[0];

  return (
    <>
      <PageHeader
        title="Period Signoff"
        description="Controller close pack: readiness, entity status, and the analyst → finance director workflow."
        actions={
          <Stack direction="row" spacing={1}>
            <Button variant="outlined" onClick={() => navigate("/exceptions/cases")}>
              Open cases
            </Button>
            <Button variant="contained">Sign off APAC E09</Button>
          </Stack>
        }
      />

      <Box
        sx={{
          p: 2,
          bgcolor: "var(--glass-bg)", backdropFilter: "blur(18px) saturate(150%)",
          border: "1px solid",
          borderColor: "primary.main",
          borderRadius: 1,
        }}
      >
        <Typography sx={{ fontSize: 11, color: "text.secondary", textTransform: "uppercase" }}>Close readiness</Typography>
        <Typography sx={{ fontFamily: '"IBM Plex Sans", sans-serif', fontSize: 40, fontWeight: 800, lineHeight: 1.1 }}>92% Ready</Typography>
        <Typography sx={{ fontSize: 12, color: "text.secondary" }}>Executive KPI for APAC E09 Q3 close</Typography>
      </Box>

      <Box sx={{ display: "grid", gridTemplateColumns: { xs: "1fr 1fr", lg: "repeat(4, 1fr)" }, gap: 2 }}>
        {closeReadiness.map((kpi) => (
          <Box key={kpi.label} className="glass" sx={{ p: 1.5, borderRadius: 2 }}>
            <Typography sx={{ fontSize: 11, color: "text.secondary", textTransform: "uppercase" }}>{kpi.label}</Typography>
            <Typography sx={{ fontFamily: '"IBM Plex Sans", sans-serif', fontSize: 20, fontWeight: 700 }}>{kpi.value}</Typography>
            {kpi.label === "Controls Passed" && (
              <Button size="small" sx={{ px: 0 }} onClick={() => setControlOpen(true)}>
                View failed control
              </Button>
            )}
          </Box>
        ))}
      </Box>

      <Box sx={{ display: "grid", gridTemplateColumns: { xs: "1fr", lg: "1.2fr 1fr 1fr" }, gap: 2.5 }}>
        <Box sx={{ p: 2, bgcolor: "var(--glass-bg)", backdropFilter: "blur(18px) saturate(150%)", border: "1px solid", borderColor: "divider", borderRadius: 1 }}>
          <Typography variant="h6" sx={{ mb: 1 }}>
            Signoff checklist
          </Typography>
          <Stack spacing={1}>
            {signoffChecklist.map((item) => (
              <Stack key={item.label} direction="row" spacing={1} alignItems="center">
                <StatusPill label={item.done ? "Done" : "Open"} tone={item.done ? "ok" : "warn"} />
                <Typography sx={{ fontSize: 13 }}>{item.label}</Typography>
              </Stack>
            ))}
          </Stack>
        </Box>
        <Box sx={{ p: 2, bgcolor: "var(--glass-bg)", backdropFilter: "blur(18px) saturate(150%)", border: "1px solid", borderColor: "divider", borderRadius: 1 }}>
          <Typography variant="h6" sx={{ mb: 1 }}>
            Exception summary
          </Typography>
          <Stack spacing={1}>
            {signoffExceptionSummary.map((item) => (
              <Stack key={item.label} direction="row" justifyContent="space-between">
                <Typography sx={{ fontSize: 12 }}>{item.label}</Typography>
                <Button size="small" onClick={() => navigate("/exceptions")}>
                  {item.value}
                </Button>
              </Stack>
            ))}
          </Stack>
        </Box>
        <Box sx={{ p: 2, bgcolor: "var(--glass-bg)", backdropFilter: "blur(18px) saturate(150%)", border: "1px solid", borderColor: "divider", borderRadius: 1 }}>
          <Typography variant="h6" sx={{ mb: 1 }}>
            Digital signature evidence
          </Typography>
          <Evidence label="Signed by" value={signoffEvidence.signedBy} />
          <Evidence label="Signed date" value={signoffEvidence.signedDate} />
          <Evidence label="Approval hash" value={signoffEvidence.approvalHash} />
          <Evidence label="Audit record ID" value={signoffEvidence.auditRecordId} />
        </Box>
      </Box>

      <Box sx={{ p: 1.5, bgcolor: "var(--glass-bg)", backdropFilter: "blur(18px) saturate(150%)", border: "1px solid", borderColor: "divider", borderRadius: 1 }}>
        <Typography variant="h6" sx={{ mb: 1 }}>
          Signoff workflow
        </Typography>
        <Stack direction="row" spacing={1} alignItems="center" flexWrap="wrap">
          {signoffFlow.map((role, index) => (
            <Stack key={role} direction="row" alignItems="center" spacing={1}>
              <Box
                sx={{
                  px: 1.25,
                  py: 0.75,
                  borderRadius: 1,
                  fontSize: 12,
                  fontWeight: 700,
                  bgcolor: index <= 2 ? "var(--indigo-soft)" : "var(--bg-muted)",
                  color: index <= 2 ? "primary.main" : "text.secondary",
                }}
              >
                {role}
              </Box>
              {index < signoffFlow.length - 1 ? <Typography sx={{ color: "text.secondary" }}>→</Typography> : null}
            </Stack>
          ))}
        </Stack>
      </Box>

      <Box sx={{ bgcolor: "var(--glass-bg)", backdropFilter: "blur(18px) saturate(150%)", border: "1px solid", borderColor: "divider", borderRadius: 1 }}>
        <Table size="small">
          <TableHead>
            <TableRow>
              <TableCell>Entity</TableCell>
              <TableCell>Status</TableCell>
              <TableCell>Exposure</TableCell>
              <TableCell>Exceptions</TableCell>
              <TableCell>Owner</TableCell>
              <TableCell>Signoff Date</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {signoffEntities.map((row) => (
              <TableRow key={row.entity} hover>
                <TableCell sx={{ fontWeight: 700 }}>{row.entity}</TableCell>
                <TableCell>
                  <StatusPill label={row.status} tone={statusTone[row.status] ?? "warn"} />
                </TableCell>
                <TableCell>{row.exposure}</TableCell>
                <TableCell>
                  <Button size="small" onClick={() => navigate("/exceptions")}>
                    {row.exceptions}
                  </Button>
                </TableCell>
                <TableCell>{row.owner}</TableCell>
                <TableCell>{row.date}</TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </Box>

      <Box sx={{ p: 2, bgcolor: "var(--glass-bg)", backdropFilter: "blur(18px) saturate(150%)", border: "1px solid", borderColor: "divider", borderRadius: 1 }}>
        <Typography variant="h6" sx={{ mb: 1 }}>
          Signoff comments
        </Typography>
        <TextField
          fullWidth
          multiline
          minRows={3}
          value={comment}
          onChange={(event) => setComment(event.target.value)}
          placeholder="Controller notes for the close pack (required for SOX evidence)."
        />
      </Box>
      <ActivityTimeline />

      <Dialog open={controlOpen} onClose={() => setControlOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle>Failed control</DialogTitle>
        <DialogContent>
          <Typography sx={{ fontWeight: 700 }}>{failed.id}</Typography>
          <Typography sx={{ fontSize: 13, mb: 1 }}>{failed.name}</Typography>
          <Typography sx={{ fontSize: 12, color: "text.secondary" }}>Owner {failed.owner}</Typography>
          <Typography sx={{ fontSize: 12, color: "text.secondary" }}>Impact {failed.impact}</Typography>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => navigate("/exceptions/investigations")}>Investigate</Button>
          <Button onClick={() => setControlOpen(false)}>Close</Button>
        </DialogActions>
      </Dialog>
    </>
  );
}

function Evidence({ label, value }: { label: string; value: string }) {
  return (
    <Stack direction="row" justifyContent="space-between" gap={2} sx={{ py: 0.75, borderBottom: "1px solid", borderColor: "divider" }}>
      <Typography sx={{ fontSize: 12, color: "text.secondary" }}>{label}</Typography>
      <Typography sx={{ fontSize: 12, fontWeight: 700, textAlign: "right" }}>{value}</Typography>
    </Stack>
  );
}
