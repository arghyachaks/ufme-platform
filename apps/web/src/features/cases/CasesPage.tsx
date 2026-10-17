import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Avatar, Box, Button, Chip, Drawer, Stack, TextField, ToggleButton, ToggleButtonGroup, Typography } from "@mui/material";
import { api } from "../../api/services";
import { useQuery } from "../../api/useQuery";
import type { CaseItem } from "../../api/types";
import { StatusPill } from "../../components/common/Panel";
import { DataTable, KeyValue, Page, StatGrid, glass, money, mono, severityTone, useToast } from "../../components/common/Blocks";

const columns: CaseItem["status"][] = ["Open", "In progress", "Pending approval", "Escalated", "Closed"];

export function CasesPage() {
  const { data, loading } = useQuery(api.cases.list);
  const [cases, setCases] = useState<CaseItem[]>([]);
  const [view, setView] = useState<"board" | "list">("board");
  const [openId, setOpenId] = useState<string | null>(null);
  const [comment, setComment] = useState("");
  const { toast, toastNode } = useToast();
  const navigate = useNavigate();

  useEffect(() => { if (data) setCases(data); }, [data]);
  const current = cases.find((c) => c.id === openId);

  const move = (id: string, status: CaseItem["status"]) => {
    setCases((cs) => cs.map((c) => (c.id === id ? { ...c, status } : c)));
    toast(`${id} → ${status}`);
  };
  const addComment = () => {
    if (!current || !comment) return;
    setCases((cs) => cs.map((c) => (c.id === current.id ? { ...c, comments: [...c.comments, { author: "You", at: "Just now", text: comment }] } : c)));
    setComment("");
  };

  const active = cases.filter((c) => c.status !== "Closed");

  return (
    <Page title="Cases" description="Assigned investigations with owners, comments, escalations, and resolutions." loading={loading}
      actions={
        <ToggleButtonGroup size="small" exclusive value={view} onChange={(_, v) => v && setView(v)}>
          <ToggleButton value="board">Board</ToggleButton>
          <ToggleButton value="list">List</ToggleButton>
        </ToggleButtonGroup>
      }>
      <StatGrid items={[
        { label: "Active cases", value: String(active.length) },
        { label: "Exposure", value: money(active.reduce((s, c) => s + c.exposure, 0)), tone: "warn" },
        { label: "Escalated", value: String(cases.filter((c) => c.status === "Escalated").length), tone: "crit" },
        { label: "Unassigned", value: String(cases.filter((c) => c.assignee === "Unassigned").length), tone: "warn" },
        { label: "Median resolution", value: "2.4 d", tone: "ok" },
      ]} />

      {view === "board" ? (
        <Box sx={{ display: "grid", gridTemplateColumns: { xs: "1fr", md: "repeat(5, minmax(200px, 1fr))" }, gap: 1.5, overflowX: "auto" }}>
          {columns.map((col) => (
            <Box key={col} sx={{ ...glass, p: 1.25, minHeight: 300 }}
              onDragOver={(e) => e.preventDefault()}
              onDrop={(e) => { const id = e.dataTransfer.getData("text/plain"); if (id) move(id, col); }}>
              <Stack direction="row" justifyContent="space-between" sx={{ mb: 1 }}>
                <Typography variant="subtitle2">{col}</Typography>
                <Chip size="small" label={cases.filter((c) => c.status === col).length} />
              </Stack>
              <Stack spacing={1}>
                {cases.filter((c) => c.status === col).map((c) => (
                  <Box key={c.id} draggable onDragStart={(e) => e.dataTransfer.setData("text/plain", c.id)} onClick={() => setOpenId(c.id)}
                    className="glass" sx={{ p: 1.25, borderRadius: 1.5, cursor: "grab", "&:hover": { borderColor: "primary.main" } }}>
                    <Stack direction="row" justifyContent="space-between" sx={{ mb: 0.5 }}>
                      <Typography sx={{ ...mono, fontSize: 11, fontWeight: 700 }}>{c.id}</Typography>
                      <StatusPill label={c.priority} tone={severityTone[c.priority]} />
                    </Stack>
                    <Typography sx={{ fontSize: 12, fontWeight: 600, mb: 0.75 }}>{c.title}</Typography>
                    <Stack direction="row" justifyContent="space-between" alignItems="center">
                      <Typography sx={{ ...mono, fontSize: 11 }}>{money(c.exposure)}</Typography>
                      <Stack direction="row" spacing={0.75} alignItems="center">
                        <Typography sx={{ fontSize: 11, color: "text.secondary" }}>{c.dueIn}</Typography>
                        <Avatar sx={{ width: 20, height: 20, fontSize: 10 }}>{c.assignee === "Unassigned" ? "?" : c.assignee.split(" ").map((p) => p[0]).join("")}</Avatar>
                      </Stack>
                    </Stack>
                  </Box>
                ))}
              </Stack>
            </Box>
          ))}
        </Box>
      ) : (
        <DataTable<CaseItem> rows={cases} rowKey={(c) => c.id} onRowClick={(c) => setOpenId(c.id)} columns={[
          { key: "id", header: "Case", render: (c) => <span style={{ ...mono, fontWeight: 700 }}>{c.id}</span> },
          { key: "t", header: "Title", render: (c) => c.title },
          { key: "e", header: "Entity", render: (c) => c.entity },
          { key: "x", header: "Exposure", align: "right", render: (c) => <span style={mono}>{money(c.exposure)}</span> },
          { key: "p", header: "Priority", render: (c) => <StatusPill label={c.priority} tone={severityTone[c.priority]} /> },
          { key: "s", header: "Status", render: (c) => c.status },
          { key: "a", header: "Assignee", render: (c) => c.assignee },
          { key: "d", header: "Due", render: (c) => c.dueIn },
        ]} />
      )}

      <Drawer anchor="right" open={Boolean(current)} onClose={() => setOpenId(null)}>
        {current ? (
          <Box sx={{ width: { xs: "100vw", sm: 440 }, p: 3 }}>
            <Typography sx={{ ...mono, fontSize: 12, color: "text.secondary" }}>{current.id}</Typography>
            <Typography variant="h6" sx={{ fontSize: 17, mb: 2 }}>{current.title}</Typography>
            <KeyValue label="Status" value={current.status} />
            <KeyValue label="Priority" value={<StatusPill label={current.priority} tone={severityTone[current.priority]} />} />
            <KeyValue label="Exposure" value={money(current.exposure)} />
            <KeyValue label="Assignee" value={current.assignee} />
            <KeyValue label="Opened / due" value={`${current.opened} · ${current.dueIn}`} />
            <KeyValue label="Linked exceptions" value={
              <Stack direction="row" spacing={0.5}>{current.exceptionIds.map((id) => (
                <Chip key={id} size="small" label={id} onClick={() => navigate(`/exceptions/investigations?id=${id}`)} />
              ))}</Stack>
            } />
            <Stack direction="row" spacing={1} sx={{ my: 2 }} flexWrap="wrap" useFlexGap>
              <Button size="small" variant="outlined" onClick={() => move(current.id, "In progress")}>Start</Button>
              <Button size="small" variant="outlined" color="error" onClick={() => move(current.id, "Escalated")}>Escalate</Button>
              <Button size="small" variant="outlined" onClick={() => move(current.id, "Pending approval")}>Submit for approval</Button>
              <Button size="small" variant="contained" color="success" onClick={() => move(current.id, "Closed")}>Close</Button>
            </Stack>
            <Typography variant="subtitle2" sx={{ mb: 1 }}>Activity</Typography>
            <Stack spacing={1.25} sx={{ mb: 2 }}>
              {current.comments.length === 0 ? <Typography sx={{ fontSize: 12, color: "text.secondary" }}>No comments yet.</Typography> : null}
              {current.comments.map((m, i) => (
                <Box key={i} sx={{ p: 1.25, borderRadius: 1, bgcolor: m.author === "AI Advisor" ? "var(--indigo-soft)" : "var(--bg-muted)" }}>
                  <Typography sx={{ fontSize: 11, fontWeight: 700 }}>{m.author} <span style={{ fontWeight: 400, opacity: 0.7 }}>· {m.at}</span></Typography>
                  <Typography sx={{ fontSize: 12 }}>{m.text}</Typography>
                </Box>
              ))}
            </Stack>
            <Stack direction="row" spacing={1}>
              <TextField size="small" fullWidth placeholder="Add a comment…" value={comment} onChange={(e) => setComment(e.target.value)} onKeyDown={(e) => e.key === "Enter" && addComment()} />
              <Button variant="contained" onClick={addComment} disabled={!comment}>Post</Button>
            </Stack>
          </Box>
        ) : null}
      </Drawer>
      {toastNode}
    </Page>
  );
}
