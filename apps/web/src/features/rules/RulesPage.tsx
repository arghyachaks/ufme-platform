import { useEffect, useState } from "react";
import { Link as RouterLink } from "react-router-dom";
import { Box, Button, Chip, Dialog, DialogActions, DialogContent, DialogTitle, MenuItem, Stack, Switch, TextField, Typography } from "@mui/material";
import { api } from "../../api/services";
import { useQuery } from "../../api/useQuery";
import type { MatchRule } from "../../api/types";
import { Panel } from "../../components/common/Panel";
import { DataTable, KeyValue, Meter, Page, StatGrid, mono, useToast } from "../../components/common/Blocks";

const emptyRule: MatchRule = { id: "", name: "", kind: "Tolerance", scope: "Intercompany", conditions: [""], priority: 7, enabled: false, hitRate: 0, precision: 0, version: "v1 draft", lastEdited: "Just now · You" };

export function RulesPage() {
  const { data, loading } = useQuery(api.rules.list);
  const [rules, setRules] = useState<MatchRule[]>([]);
  const [selectedId, setSelectedId] = useState<string>();
  const [draft, setDraft] = useState<MatchRule | null>(null);
  const { toast, toastNode } = useToast();
  useEffect(() => { if (data) { setRules(data); setSelectedId(data[0]?.id); } }, [data]);
  const selected = rules.find((r) => r.id === selectedId);

  const toggle = async (id: string) => {
    const rule = rules.find((r) => r.id === id);
    if (!rule) return;
    setRules((rs) => rs.map((r) => (r.id === id ? { ...r, enabled: !r.enabled } : r)));
    try {
      await api.rules.setEnabled(id, !rule.enabled);
      toast(`${id} ${rule.enabled ? "disabled" : "enabled"} — applies from the next run`);
    } catch {
      setRules((rs) => rs.map((r) => (r.id === id ? { ...r, enabled: rule.enabled } : r)));
      toast(`Could not update ${id}`);
    }
  };
  const save = () => {
    if (!draft) return;
    const isNew = !draft.id;
    const rule = isNew ? { ...draft, id: `R-00${rules.length + 1}` } : draft;
    setRules((rs) => (isNew ? [...rs, rule] : rs.map((r) => (r.id === rule.id ? rule : r))));
    setSelectedId(rule.id);
    setDraft(null);
    toast(isNew ? `${rule.id} saved as draft` : `${rule.id} updated — publish requires controller approval`);
  };

  const enabled = rules.filter((r) => r.enabled);
  return (
    <Page title="Matching rules" description="Exact, tolerance, near-match and many-to-many rules, applied in priority order before smart ranking." loading={loading}
      actions={<Button variant="contained" onClick={() => setDraft({ ...emptyRule })}>New rule</Button>}>
      <StatGrid items={[
        { label: "Active rules", value: `${enabled.length}/${rules.length}` },
        { label: "Rule coverage", value: `${enabled.reduce((s, r) => s + r.hitRate, 0).toFixed(1)}%`, tone: "ok", hint: "Of matched volume" },
        { label: "Weighted precision", value: `${(enabled.reduce((s, r) => s + r.precision * r.hitRate, 0) / Math.max(enabled.reduce((s, r) => s + r.hitRate, 0), 1)).toFixed(1)}%`, tone: "ok" },
        { label: "Pending publish", value: String(rules.filter((r) => r.version.includes("draft")).length), tone: "warn" },
      ]} />
      <Box sx={{ display: "grid", gridTemplateColumns: { xs: "1fr", lg: "1.6fr 1fr" }, gap: 2.5, alignItems: "start" }}>
        <DataTable<MatchRule> rows={[...rules].sort((a, b) => a.priority - b.priority)} rowKey={(r) => r.id} selectedKey={selectedId} onRowClick={(r) => setSelectedId(r.id)} columns={[
          { key: "p", header: "#", render: (r) => r.priority, width: 30 },
          { key: "n", header: "Rule", render: (r) => <><Typography sx={{ fontSize: 12, fontWeight: 600 }}>{r.name}</Typography><Typography sx={{ ...mono, fontSize: 11, color: "text.secondary" }}>{r.id} · {r.version}</Typography></> },
          { key: "k", header: "Type", render: (r) => <Chip size="small" label={r.kind} variant="outlined" /> },
          { key: "s", header: "Scope", render: (r) => r.scope },
          { key: "h", header: "Hit rate", render: (r) => <Stack><span style={mono}>{r.hitRate}%</span><Meter value={r.hitRate} max={70} tone="ok" /></Stack> },
          { key: "pr", header: "Precision", render: (r) => <span style={mono}>{r.precision ? `${r.precision}%` : "—"}</span> },
          { key: "e", header: "On", render: (r) => <Switch size="small" checked={r.enabled} onClick={(e) => e.stopPropagation()} onChange={() => toggle(r.id)} /> },
        ]} />
        {selected ? (
          <Panel title={selected.name} action={<Button size="small" onClick={() => setDraft({ ...selected })}>Edit</Button>}>
            <KeyValue label="Type / scope" value={`${selected.kind} · ${selected.scope}`} />
            {selected.tolerance ? <KeyValue label="Tolerance" value={selected.tolerance} /> : null}
            <KeyValue label="Version" value={selected.version} />
            <KeyValue label="Last edited" value={selected.lastEdited} />
            <Typography variant="subtitle2" sx={{ mt: 2, mb: 1 }}>Conditions (all must hold)</Typography>
            <Stack spacing={0.75}>
              {selected.conditions.map((c, i) => (
                <Box key={i} sx={{ ...mono, fontSize: 12, px: 1.25, py: 0.75, borderRadius: 1, bgcolor: "var(--indigo-soft)" }}>{i > 0 ? "AND " : "IF "}{c}</Box>
              ))}
              <Box sx={{ ...mono, fontSize: 12, px: 1.25, py: 0.75, borderRadius: 1, bgcolor: "var(--emerald-soft)" }}>THEN propose match ({selected.kind === "Many-to-many" ? "1:M / M:M" : "1:1"})</Box>
            </Stack>
            <Stack direction="row" spacing={1} sx={{ mt: 2 }}>
              <Button size="small" variant="outlined" component={RouterLink} to="/rules/simulation">Simulate</Button>
              <Button size="small" variant="contained" onClick={() => toast(`${selected.id} submitted for publish approval`)}>Submit for publish</Button>
            </Stack>
          </Panel>
        ) : null}
      </Box>

      <Dialog open={Boolean(draft)} onClose={() => setDraft(null)} fullWidth maxWidth="sm">
        <DialogTitle>{draft?.id ? `Edit ${draft.id}` : "New matching rule"}</DialogTitle>
        {draft ? (
          <DialogContent>
            <Stack spacing={2} sx={{ pt: 1 }}>
              <TextField label="Name" size="small" value={draft.name} onChange={(e) => setDraft({ ...draft, name: e.target.value })} />
              <Stack direction="row" spacing={2}>
                <TextField select label="Type" size="small" fullWidth value={draft.kind} onChange={(e) => setDraft({ ...draft, kind: e.target.value as MatchRule["kind"] })}>
                  {["Exact", "Tolerance", "Fuzzy", "Many-to-many"].map((k) => <MenuItem key={k} value={k}>{k}</MenuItem>)}
                </TextField>
                <TextField select label="Scope" size="small" fullWidth value={draft.scope} onChange={(e) => setDraft({ ...draft, scope: e.target.value })}>
                  {["Intercompany", "Bank", "AP / AR", "Journal", "Inventory", "Payroll"].map((k) => <MenuItem key={k} value={k}>{k}</MenuItem>)}
                </TextField>
                <TextField label="Priority" size="small" type="number" sx={{ width: 110 }} value={draft.priority} onChange={(e) => setDraft({ ...draft, priority: Number(e.target.value) })} />
              </Stack>
              {draft.kind === "Tolerance" ? <TextField label="Tolerance" size="small" placeholder="e.g. 0.5% / 3d" value={draft.tolerance ?? ""} onChange={(e) => setDraft({ ...draft, tolerance: e.target.value })} /> : null}
              <Typography variant="subtitle2">Conditions</Typography>
              {draft.conditions.map((c, i) => (
                <TextField key={i} size="small" placeholder="field operator value, e.g. |amount Δ| ≤ 0.5%" value={c} InputProps={{ sx: mono }}
                  onChange={(e) => setDraft({ ...draft, conditions: draft.conditions.map((x, j) => (j === i ? e.target.value : x)) })} />
              ))}
              <Button size="small" sx={{ alignSelf: "flex-start" }} onClick={() => setDraft({ ...draft, conditions: [...draft.conditions, ""] })}>+ Add condition</Button>
            </Stack>
          </DialogContent>
        ) : null}
        <DialogActions>
          <Button onClick={() => setDraft(null)}>Cancel</Button>
          <Button variant="contained" disabled={!draft?.name} onClick={save}>Save draft</Button>
        </DialogActions>
      </Dialog>
      {toastNode}
    </Page>
  );
}
