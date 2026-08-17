import { Box, Button, Stack, Table, TableBody, TableCell, TableHead, TableRow, Typography } from "@mui/material";
import { PageHeader } from "../../components/common/PageHeader";
import { StatusPill } from "../../components/common/Panel";
import { ActivityTimeline } from "./ActivityTimeline";
import { closeReadiness, signoffEntities, signoffFlow } from "./data";

const statusTone: Record<string, "ok" | "warn" | "crit"> = {
  "Signed off": "ok",
  "Manager signed": "warn",
  "Pending controller": "crit",
};

export function SignoffPage() {
  return (
    <>
      <PageHeader
        title="Period Signoff"
        description="Controller close pack: readiness, entity status, and the analyst → finance director workflow."
        actions={
          <Button variant="contained">Sign off APAC E09</Button>
        }
      />

      <Box sx={{ display: "grid", gridTemplateColumns: { xs: "1fr 1fr", lg: "repeat(4, 1fr)" }, gap: 2 }}>
        {closeReadiness.map((kpi) => (
          <Box key={kpi.label} sx={{ p: 1.5, bgcolor: "background.paper", border: "1px solid", borderColor: "divider", borderRadius: 1 }}>
            <Typography sx={{ fontSize: 11, color: "text.secondary", textTransform: "uppercase" }}>{kpi.label}</Typography>
            <Typography sx={{ fontFamily: '"IBM Plex Sans", sans-serif', fontSize: 20, fontWeight: 700 }}>{kpi.value}</Typography>
          </Box>
        ))}
      </Box>

      <Box sx={{ p: 1.5, bgcolor: "background.paper", border: "1px solid", borderColor: "divider", borderRadius: 1 }}>
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

      <Box sx={{ bgcolor: "background.paper", border: "1px solid", borderColor: "divider", borderRadius: 1 }}>
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
                <TableCell>{row.exceptions}</TableCell>
                <TableCell>{row.owner}</TableCell>
                <TableCell>{row.date}</TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </Box>
      <ActivityTimeline />
    </>
  );
}
