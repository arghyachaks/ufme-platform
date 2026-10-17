import { useState } from "react";
import { Box, Button, Chip, Stack, Typography } from "@mui/material";
import { api } from "../../api/services";
import { useQuery } from "../../api/useQuery";
import { Panel, StatusPill } from "../../components/common/Panel";
import { KeyValue, Page, StatGrid, glass, useToast } from "../../components/common/Blocks";

const statusTone = { Published: "ok", Draft: "warn", Retired: "crit" } as const;

export function PoliciesPage() {
  const { data = [], loading } = useQuery(api.policies.list);
  const [selectedId, setSelectedId] = useState<string>();
  const { toast, toastNode } = useToast();
  const selected = data.find((p) => p.id === selectedId) ?? data[0];

  return (
    <Page title="Policies" description="Versioned tolerance, approval, segregation-of-duties, materiality, and retention policies that govern matching and workflow." loading={loading}
      actions={<Button variant="contained" onClick={() => toast("New policy draft created")}>New policy</Button>}>
      <StatGrid items={[
        { label: "Published", value: String(data.filter((p) => p.status === "Published").length), tone: "ok" },
        { label: "Drafts", value: String(data.filter((p) => p.status === "Draft").length), tone: "warn" },
        { label: "Policy exceptions (30d)", value: "17", hint: "Approved overrides" },
        { label: "Next review", value: "01 Oct 2026" },
      ]} />
      {selected ? (
        <Box sx={{ display: "grid", gridTemplateColumns: { xs: "1fr", lg: "1fr 1.3fr" }, gap: 2.5, alignItems: "start" }}>
          <Stack spacing={1.25}>
            {data.map((p) => (
              <Box key={p.id} onClick={() => setSelectedId(p.id)} sx={{ ...glass, p: 1.75, cursor: "pointer", borderColor: p.id === selected.id ? "primary.main" : "divider" }}>
                <Stack direction="row" justifyContent="space-between" alignItems="center">
                  <Typography sx={{ fontSize: 13, fontWeight: 700 }}>{p.name}</Typography>
                  <StatusPill label={p.status} tone={statusTone[p.status]} />
                </Stack>
                <Typography sx={{ fontSize: 12, color: "text.secondary", mt: 0.5 }}>{p.category} · v{p.version} · {p.owner}</Typography>
              </Box>
            ))}
          </Stack>
          <Panel title={`${selected.name} · v${selected.version}`} action={<Chip size="small" label={selected.category} />}>
            <Typography sx={{ fontSize: 13, mb: 2 }}>{selected.summary}</Typography>
            <Typography variant="subtitle2" sx={{ mb: 1 }}>Thresholds</Typography>
            <Box sx={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(140px, 1fr))", gap: 1.25, mb: 2 }}>
              {selected.thresholds.map((t) => (
                <Box key={t.label} className="glass" sx={{ p: 1.25, borderRadius: 1.5 }}>
                  <Typography sx={{ fontSize: 11, color: "text.secondary" }}>{t.label}</Typography>
                  <Typography sx={{ fontSize: 16, fontWeight: 700 }}>{t.value}</Typography>
                </Box>
              ))}
            </Box>
            <KeyValue label="Owner" value={selected.owner} />
            <KeyValue label="Effective" value={selected.effective} />
            <KeyValue label="Applies to" value="All legal entities" />
            <Typography variant="subtitle2" sx={{ mt: 2, mb: 1 }}>Version history</Typography>
            <Stack spacing={0.5}>
              {[selected.version, "previous", "initial"].map((v, i) => (
                <Typography key={v} sx={{ fontSize: 12, color: i ? "text.secondary" : "text.primary" }}>
                  {i === 0 ? `v${v} — current` : i === 1 ? "Prior version — approved by CFO Office" : "Initial version — imported from policy manual"}
                </Typography>
              ))}
            </Stack>
            <Stack direction="row" spacing={1} sx={{ mt: 2 }}>
              <Button size="small" variant="outlined" onClick={() => toast("Diff opened against previous version")}>Compare versions</Button>
              {selected.status === "Draft"
                ? <Button size="small" variant="contained" onClick={() => toast(`${selected.name} sent for approval`)}>Submit for approval</Button>
                : <Button size="small" variant="outlined" onClick={() => toast(`Draft v-next of ${selected.name} created`)}>Create new version</Button>}
            </Stack>
          </Panel>
        </Box>
      ) : null}
      {toastNode}
    </Page>
  );
}
