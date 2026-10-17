import { Fragment } from "react";
import { Box, Button, Chip, Stack, Typography } from "@mui/material";
import ArrowForwardIcon from "@mui/icons-material/ArrowForward";
import { api } from "../../api/services";
import { useQuery } from "../../api/useQuery";
import type { WorkflowStage } from "../../api/types";
import { Panel } from "../../components/common/Panel";
import { DataTable, Page, glass, useToast } from "../../components/common/Blocks";

export function WorkflowPage() {
  const { data = [], loading } = useQuery(api.workflow.stages);
  const { toast, toastNode } = useToast();
  return (
    <Page title="Workflow" description="How matches flow from the engine through review, approval tiers, and period sign-off — with SLAs and escalation paths." loading={loading}
      actions={<Button variant="contained" onClick={() => toast("Workflow v7 draft created")}>Edit workflow</Button>}>
      <Panel title="Flow">
        <Stack direction="row" alignItems="center" sx={{ overflowX: "auto", pb: 1 }} spacing={1}>
          {data.map((s, i) => (
            <Fragment key={s.name}>
              <Box sx={{ ...glass, p: 1.5, minWidth: 160, borderColor: i === 0 ? "success.main" : "divider" }}>
                <Typography sx={{ fontSize: 12, fontWeight: 700 }}>{s.name}</Typography>
                <Typography sx={{ fontSize: 11, color: "text.secondary" }}>{s.role}</Typography>
                <Chip size="small" sx={{ mt: 0.75 }} label={s.slaHours ? `SLA ${s.slaHours}h` : "Instant"} />
              </Box>
              {i < data.length - 1 ? <ArrowForwardIcon fontSize="small" sx={{ color: "text.secondary", flexShrink: 0 }} /> : null}
            </Fragment>
          ))}
        </Stack>
      </Panel>
      <DataTable<WorkflowStage> rows={data} rowKey={(s) => s.name} columns={[
        { key: "n", header: "Stage", render: (s) => <b>{s.name}</b> },
        { key: "r", header: "Owner role", render: (s) => s.role },
        { key: "c", header: "Entry condition", render: (s) => <span style={{ fontFamily: "IBM Plex Sans" }}>{s.condition}</span> },
        { key: "s", header: "SLA", render: (s) => (s.slaHours ? `${s.slaHours} h` : "—") },
        { key: "e", header: "Escalates to", render: (s) => s.escalateTo ?? "—" },
      ]} />
      <Box sx={{ display: "grid", gridTemplateColumns: { xs: "1fr", md: "1fr 1fr" }, gap: 2.5 }}>
        <Panel title="Guardrails">
          {["Preparer cannot approve own match (SOD-01)", "Exposure > 1M requires dual approval (IC-07)", "Rule changes require controller approval before publish", "Signoff blocked while any control is failing"].map((g) => (
            <Typography key={g} sx={{ fontSize: 12, mb: 0.75 }}>• {g}</Typography>
          ))}
        </Panel>
        <Panel title="Notifications">
          {["SLA at 75% → reminder to owner", "SLA breached → escalate + notify manager", "Case escalated → email controller", "Daily digest at 08:00 local"].map((g) => (
            <Typography key={g} sx={{ fontSize: 12, mb: 0.75 }}>• {g}</Typography>
          ))}
        </Panel>
      </Box>
      {toastNode}
    </Page>
  );
}
