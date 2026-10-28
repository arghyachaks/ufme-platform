import { useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { Box, Button, Divider, Stack, Typography } from "@mui/material";
import { api, ApiError } from "../../api/services";
import { useQuery } from "../../api/useQuery";
import { Panel, StatusPill } from "../../components/common/Panel";
import { DataTable, KeyValue, Page, glass, money, mono, severityTone, useToast } from "../../components/common/Blocks";

const hypotheses = (cause: string) => [
  { text: cause, score: 0.72 },
  { text: "Posting period cut-off", score: 0.16 },
  { text: "Partial settlement awaiting second leg", score: 0.08 },
];

export function InvestigationsPage() {
  const { data = [], loading, reload } = useQuery(api.exceptions.list);
  const [params, setParams] = useSearchParams();
  const navigate = useNavigate();
  const { toast, toastNode } = useToast();
  const [note, setNote] = useState("");
  const open = data.filter((e) => e.status !== "Resolved");
  const current = open.find((e) => e.id === params.get("id")) ?? open[0];
  const fail = (e: unknown) => toast(e instanceof ApiError ? e.message : String(e));
  const createCase = (id: string) =>
    api.workflow.createCase([id]).then((c) => toast(`${c.id} opened for ${id}`)).catch(fail);
  const resolve = (id: string) =>
    api.workflow
      .setExceptionStatus(id, "Resolved", note || undefined)
      .then(() => {
        toast(`${id} resolved and recorded in the audit trail`);
        setNote("");
        reload();
      })
      .catch(fail);
  const addNote = (id: string, status: string) =>
    api.workflow
      .setExceptionStatus(id, status, note)
      .then(() => {
        toast("Note added to the audit trail");
        setNote("");
      })
      .catch(fail);

  return (
    <Page title="Investigations" description="Deep-dive an unmatched item: evidence, likely root cause, nearest candidates, and lineage." loading={loading}>
      {current ? (
        <Box sx={{ display: "grid", gridTemplateColumns: { xs: "1fr", lg: "320px 1fr" }, gap: 2.5 }}>
          <Box sx={{ ...glass, maxHeight: 640, overflowY: "auto" }}>
            {open.map((e) => (
              <Box key={e.id} onClick={() => setParams({ id: e.id })}
                sx={{ px: 2, py: 1.25, cursor: "pointer", borderBottom: "1px solid", borderColor: "divider", bgcolor: e.id === current.id ? "var(--indigo-soft)" : "transparent" }}>
                <Stack direction="row" justifyContent="space-between">
                  <Typography sx={{ ...mono, fontSize: 12, fontWeight: 700 }}>{e.id}</Typography>
                  <StatusPill label={e.severity} tone={severityTone[e.severity]} />
                </Stack>
                <Typography sx={{ fontSize: 12, color: "text.secondary" }}>{e.entity} ↔ {e.counterparty} · {e.type}</Typography>
                <Typography sx={{ ...mono, fontSize: 12 }}>{money(e.amount, e.currency)}</Typography>
              </Box>
            ))}
          </Box>

          <Stack spacing={2.5}>
            <Panel title={`${current.id} · ${current.type}`} action={
              <Stack direction="row" spacing={1}>
                <Button size="small" variant="outlined" onClick={() => navigate("/reconciliation/manual-match")}>Manual match</Button>
                <Button size="small" variant="outlined" onClick={() => void createCase(current.id)}>Create case</Button>
                <Button size="small" variant="contained" onClick={() => void resolve(current.id)}>Resolve</Button>
              </Stack>
            }>
              <Box sx={{ display: "grid", gridTemplateColumns: { xs: "1fr", md: "1fr 1fr" }, gap: 3 }}>
                <Box>
                  <KeyValue label="Entity / counterparty" value={`${current.entity} ↔ ${current.counterparty}`} />
                  <KeyValue label="Amount" value={money(current.amount, current.currency)} />
                  <KeyValue label="Age" value={`${current.ageDays} days`} />
                  <KeyValue label="SLA" value={current.slaHoursLeft < 0 ? `${-current.slaHoursLeft}h overdue` : `${current.slaHoursLeft}h left`} />
                  <KeyValue label="Owner" value={current.owner} />
                  <KeyValue label="Status" value={current.status} />
                </Box>
                <Box>
                  <Typography variant="subtitle2" sx={{ mb: 1 }}>Likely root causes</Typography>
                  {hypotheses(current.rootCause).map((h) => (
                    <Stack key={h.text} direction="row" spacing={1} alignItems="center" sx={{ mb: 1 }}>
                      <Box sx={{ width: `${h.score * 100}%`, maxWidth: 160, minWidth: 8, height: 8, borderRadius: 4, bgcolor: "primary.main", opacity: 0.3 + h.score }} />
                      <Typography sx={{ fontSize: 12, flex: 1 }}>{h.text}</Typography>
                      <Typography sx={{ ...mono, fontSize: 12 }}>{Math.round(h.score * 100)}%</Typography>
                    </Stack>
                  ))}
                  <Button size="small" sx={{ mt: 1 }} onClick={() => navigate("/data/lineage")}>View lineage →</Button>
                </Box>
              </Box>
            </Panel>

            <Panel title="Nearest candidates">
              <DataTable
                rows={[
                  { id: "TXN-B-55120", side: current.counterparty, amount: current.amount * 0.997, date: "Δ 2 d", score: 0.78, reason: "Amount within 0.3%, FX source differs" },
                  { id: "TXN-B-55133", side: current.counterparty, amount: current.amount * 0.5, date: "Δ 4 d", score: 0.64, reason: "Possible partial settlement (1 of 2)" },
                  { id: "TXN-B-55009", side: current.counterparty, amount: current.amount, date: "Δ 19 d", score: 0.41, reason: "Exact amount, outside date window" },
                ]}
                rowKey={(r) => r.id}
                columns={[
                  { key: "id", header: "Candidate", render: (r) => <span style={mono}>{r.id}</span> },
                  { key: "side", header: "Side B", render: (r) => r.side },
                  { key: "amt", header: "Amount", align: "right", render: (r) => <span style={mono}>{money(r.amount, current.currency)}</span> },
                  { key: "date", header: "Date", render: (r) => r.date },
                  { key: "score", header: "Score", render: (r) => <span style={mono}>{r.score.toFixed(2)}</span> },
                  { key: "why", header: "Why", render: (r) => r.reason },
                ]}
              />
            </Panel>

            <Panel title="Evidence & notes">
              <Stack direction="row" spacing={1} flexWrap="wrap" sx={{ mb: 2 }}>
                {["Source document.pdf", "Bank statement line", "ERP journal entry", "Counterparty confirmation.eml"].map((f) => (
                  <Button key={f} size="small" variant="outlined" onClick={() => toast(`Previewing ${f}`)}>{f}</Button>
                ))}
              </Stack>
              <Divider sx={{ mb: 1.5 }} />
              <Stack direction="row" spacing={1}>
                <Box component="input" value={note} onChange={(e: React.ChangeEvent<HTMLInputElement>) => setNote(e.target.value)} placeholder="Add an investigation note…"
                  sx={{ flex: 1, px: 1.5, py: 1, border: "1px solid", borderColor: "divider", borderRadius: 1, bgcolor: "transparent", color: "text.primary", font: "inherit", fontSize: 13 }} />
                <Button variant="contained" disabled={!note} onClick={() => void addNote(current.id, current.status)}>Add</Button>
              </Stack>
            </Panel>
          </Stack>
        </Box>
      ) : (
        <Typography color="text.secondary">No open exceptions.</Typography>
      )}
      {toastNode}
    </Page>
  );
}
