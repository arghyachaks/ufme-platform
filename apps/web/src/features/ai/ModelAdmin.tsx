import { useState } from "react";
import { Box, Button, Checkbox, Dialog, DialogActions, DialogContent, DialogTitle, FormControlLabel, MenuItem, Select, Stack, TextField, Typography } from "@mui/material";
import { api, ApiError } from "../../api/services";
import { useQuery } from "../../api/useQuery";
import type { AgentModel, NewAgentModel } from "../../api/types";
import { Panel, StatusPill } from "../../components/common/Panel";
import { DataTable, mono, useToast } from "../../components/common/Blocks";

const PROVIDERS = ["ollama", "openai", "anthropic", "azure_openai", "bedrock_converse", "google_vertexai", "mistralai", "openai-compatible-local"];
const ROLE_LABEL: Record<string, string> = { default: "All agents (default)", assist: "ufme Assist", investigator: "Recon Investigator", researcher: "Research sub-agents" };
const TONE = { approved: "ok", pending: "warn", blocked: "crit" } as const;

/** Model inventory with administration: register (any provider), approve with four eyes, block, and choose which
 *  model each agent uses. The server enforces the roles; this screen just offers the actions. */
export function ModelAdmin() {
  const q = useQuery(api.agents.models);
  const { toast, toastNode } = useToast();
  const [open, setOpen] = useState(false);
  const act = async (fn: () => Promise<unknown>, ok: string) => {
    try {
      await fn();
      toast(ok);
      q.reload();
    } catch (e) {
      toast(e instanceof ApiError ? e.message : "That didn't work.");
    }
  };
  const models = q.data?.models ?? [];
  const approved = models.filter((m) => m.status === "approved").map((m) => m.name);
  const bindings = q.data?.bindings ?? {};

  return (
    <Panel title="Model inventory and controls" action={<Button size="small" variant="outlined" onClick={() => setOpen(true)}>Register a model</Button>}>
      <DataTable<AgentModel>
        rows={models}
        rowKey={(r) => r.name}
        columns={[
          { key: "n", header: "Name", render: (r) => <span style={mono}>{r.name}</span> },
          { key: "p", header: "Provider · model", render: (r) => `${r.provider} · ${r.model}` },
          { key: "w", header: "Runs where", render: (r) => (r.local ? "On-premise" : "Hosted: data leaves network") },
          { key: "s", header: "Status", render: (r) => <StatusPill label={r.status[0].toUpperCase() + r.status.slice(1)} tone={TONE[r.status as keyof typeof TONE] ?? "warn"} /> },
          { key: "r", header: "Requested · approved", render: (r) => (r.registered ? `${r.requestedBy ?? "—"} · ${r.approvedBy ?? "—"}` : "Configured by IT") },
          { key: "c", header: "Price / 1K tokens", align: "right", render: (r) => (r.priceIn || r.priceOut ? `$${r.priceIn} · $${r.priceOut}` : "Free") },
          { key: "k", header: "Key", render: (r) => (r.keyConfigured == null ? "Not needed" : r.keyConfigured ? "Configured" : "Missing") },
          {
            key: "a",
            header: "",
            render: (r) =>
              r.registered ? (
                <Stack direction="row" spacing={1}>
                  {r.status === "pending" && <Button size="small" onClick={() => act(() => api.agents.approve(r.name), `${r.name} approved`)}>Approve</Button>}
                  {r.status !== "blocked" && <Button size="small" color="error" onClick={() => act(() => api.agents.block(r.name), `${r.name} blocked`)}>Block</Button>}
                </Stack>
              ) : null,
          },
        ]}
      />
      <Typography sx={{ fontSize: 15, fontWeight: 600, mt: 2.5, mb: 1 }}>Which model each agent uses</Typography>
      <Stack spacing={1}>
        {(q.data?.roles ?? []).map((role) => {
          const current = bindings[role] ?? bindings.default ?? [];
          return (
            <Stack key={role} direction="row" spacing={2} alignItems="center" flexWrap="wrap">
              <Typography sx={{ fontSize: 13, minWidth: 180 }}>{ROLE_LABEL[role] ?? role}</Typography>
              <Select
                size="small"
                value={current[0] ?? ""}
                onChange={(e) => {
                  const first = String(e.target.value);
                  const chain = [first, ...(first === "local-default" ? [] : ["local-default"])];
                  void act(() => api.agents.bind(role, chain), `${ROLE_LABEL[role] ?? role} now uses ${first}`);
                }}
                sx={{ minWidth: 220, fontSize: 13 }}
              >
                {approved.map((n) => <MenuItem key={n} value={n}>{n}</MenuItem>)}
              </Select>
              <Typography sx={{ ...mono, fontSize: 11.5, color: "text.secondary" }}>fallback: {current.slice(1).join(" → ") || "none"}</Typography>
            </Stack>
          );
        })}
      </Stack>
      <Typography sx={{ fontSize: 12, color: "text.secondary", mt: 2 }}>
        Controllers and Finance Directors register models and choose bindings. A Finance Director other than the requester approves a model before any agent may use it. API keys are never entered here: give the name of the secret that holds the key.
      </Typography>
      <RegisterDialog open={open} onClose={() => setOpen(false)} onSave={(m) => act(() => api.agents.propose(m), `${m.name} registered, waiting for approval`).then(() => setOpen(false))} />
      {toastNode}
    </Panel>
  );
}

function RegisterDialog({ open, onClose, onSave }: { open: boolean; onClose: () => void; onSave: (m: NewAgentModel) => void }) {
  const [m, setM] = useState<NewAgentModel>({ name: "", provider: "ollama", model: "" });
  const set = (k: keyof NewAgentModel) => (e: { target: { value: string } }) => setM({ ...m, [k]: e.target.value });
  const hosted = !["ollama", "openai-compatible-local"].includes(m.provider);
  return (
    <Dialog open={open} onClose={onClose} fullWidth maxWidth="sm">
      <DialogTitle>Register a model</DialogTitle>
      <DialogContent>
        <Stack spacing={2} sx={{ pt: 1 }}>
          <TextField size="small" label="Short name" value={m.name} onChange={set("name")} helperText="e.g. claude-sonnet, gpt-mini, llama-local" />
          <Select size="small" value={m.provider} onChange={(e) => setM({ ...m, provider: String(e.target.value) })}>
            {PROVIDERS.map((p) => <MenuItem key={p} value={p}>{p}</MenuItem>)}
          </Select>
          <TextField size="small" label="Provider's model id" value={m.model} onChange={set("model")} />
          <TextField size="small" label="Endpoint URL (optional)" value={m.baseUrl ?? ""} onChange={set("baseUrl")} />
          {hosted && <TextField size="small" label="Secret name holding the API key" value={m.apiKeyEnv ?? ""} onChange={set("apiKeyEnv")} helperText="The NAME of the environment variable / secret, never the key itself" />}
          <Stack direction="row" spacing={2}>
            <TextField size="small" type="number" label="$ per 1K input tokens" value={m.priceIn ?? ""} onChange={(e) => setM({ ...m, priceIn: Number(e.target.value) })} />
            <TextField size="small" type="number" label="$ per 1K output tokens" value={m.priceOut ?? ""} onChange={(e) => setM({ ...m, priceOut: Number(e.target.value) })} />
          </Stack>
          <FormControlLabel control={<Checkbox checked={Boolean(m.allowsConfidential)} onChange={(e) => setM({ ...m, allowsConfidential: e.target.checked })} />} label="Approved for confidential data" />
          <TextField size="small" label="Why this model (for the approver)" value={m.note ?? ""} onChange={set("note")} multiline minRows={2} />
          {hosted && <Box sx={{ fontSize: 12.5, bgcolor: "var(--amber-soft)", p: 1.25 }}>Hosted model: questions and the data agents look up will be sent to {m.provider}. A Finance Director must approve it.</Box>}
        </Stack>
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose}>Cancel</Button>
        <Button variant="contained" disabled={!m.name || !m.model} onClick={() => onSave(m)}>Submit for approval</Button>
      </DialogActions>
    </Dialog>
  );
}
