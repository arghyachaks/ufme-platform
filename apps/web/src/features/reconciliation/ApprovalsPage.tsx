import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { Box, Button, Stack, Table, TableBody, TableCell, TableHead, TableRow, Typography } from "@mui/material";
import { PageHeader } from "../../components/common/PageHeader";
import { ActivityTimeline } from "./ActivityTimeline";
import { approvalKpis, approvals } from "./data";

export function ApprovalsPage() {
  const [selectedId, setSelectedId] = useState(approvals[0]?.id);
  const selected = approvals.find((row) => row.id === selectedId) ?? approvals[0];
  const navigate = useNavigate();

  return (
    <>
      <PageHeader
        title="Approvals"
        description="Controller queue for submitted matches. Approve, reject, or request information with a full audit trail."
      />
      <Box sx={{ display: "grid", gridTemplateColumns: { xs: "1fr 1fr", lg: "repeat(4, 1fr)" }, gap: 2 }}>
        {approvalKpis.map((kpi) => (
          <Box key={kpi.label} sx={{ p: 1.5, bgcolor: "background.paper", border: "1px solid", borderColor: "divider", borderRadius: 1 }}>
            <Typography sx={{ fontSize: 11, color: "text.secondary", textTransform: "uppercase" }}>{kpi.label}</Typography>
            <Typography sx={{ fontFamily: '"IBM Plex Sans", sans-serif', fontSize: 20, fontWeight: 700 }}>{kpi.value}</Typography>
          </Box>
        ))}
      </Box>

      <Box sx={{ display: "grid", gridTemplateColumns: { xs: "1fr", lg: "1.5fr 1fr" }, gap: 2.5 }}>
        <Box sx={{ bgcolor: "background.paper", border: "1px solid", borderColor: "divider", borderRadius: 1 }}>
          <Table size="small">
            <TableHead>
              <TableRow>
                <TableCell>Match ID</TableCell>
                <TableCell>Submitted By</TableCell>
                <TableCell>Entity</TableCell>
                <TableCell>Exposure</TableCell>
                <TableCell>Confidence</TableCell>
                <TableCell>Date</TableCell>
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
                  <TableCell sx={{ fontFamily: '"IBM Plex Sans", sans-serif', fontWeight: 700 }}>{row.id}</TableCell>
                  <TableCell>{row.submittedBy}</TableCell>
                  <TableCell>{row.entity}</TableCell>
                  <TableCell>{row.exposure}</TableCell>
                  <TableCell>{row.confidence}</TableCell>
                  <TableCell>{row.date}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </Box>

        <Box sx={{ p: 2, bgcolor: "background.paper", border: "1px solid", borderColor: "divider", borderRadius: 1 }}>
          <Typography variant="h6">{selected.id}</Typography>
          <Typography sx={{ fontSize: 12, color: "text.secondary", mb: 1.5 }}>
            {selected.entity} · {selected.exposure}
          </Typography>
          <Typography sx={{ fontSize: 12, fontWeight: 700 }}>Rationale</Typography>
          <Typography sx={{ fontSize: 12, mb: 1.5 }}>{selected.rationale}</Typography>
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
          </Stack>
        </Box>
      </Box>
      <ActivityTimeline />
    </>
  );
}
