import { useState } from "react";
import { Box, ButtonBase, CircularProgress, Stack, Typography } from "@mui/material";
import CheckRoundedIcon from "@mui/icons-material/CheckRounded";
import CloseRoundedIcon from "@mui/icons-material/CloseRounded";
import ExpandMoreRoundedIcon from "@mui/icons-material/ExpandMoreRounded";
import type { AgentEvent, AgentTodo } from "../../api/types";

/** What an agent did on one answer: built up from the harness event stream, rendered as the "Working" panel. */
export type Work = {
  runId?: string;
  model?: string;
  local?: boolean;
  thinking: string[];
  todos: AgentTodo[];
  steps: Step[]; // tool calls and sub-agents, in the order they started
  drafts: { msg: string | null; text: string }[];
  working: string[]; // message ids that turned out to be working text, not the answer
  answer?: string;
  usage?: Extract<AgentEvent, { type: "usage" }>;
  error?: string;
  finished?: boolean;
};
type Step = { id: string; kind: "task" | "subagent"; label: string; detail?: string; agent?: string; status: "running" | "done" | "error"; summary?: string };

export const emptyWork = (): Work => ({ thinking: [], todos: [], steps: [], drafts: [], working: [] });

const TOOL_LABEL: Record<string, string> = {
  close_overview: "Reading the close overview",
  list_exceptions: "Looking up exceptions",
  list_cases: "Looking up cases",
  latest_matching_run: "Checking the latest matching run",
  review_queue: "Reading the review queue",
  open_approvals: "Checking open approvals",
  close_readiness: "Checking sign-off readiness",
};

function argText(args?: Record<string, unknown>) {
  const parts = Object.entries(args ?? {}).filter(([, v]) => v !== "" && v != null).map(([k, v]) => `${k}: ${String(v)}`);
  return parts.length ? parts.join(" · ") : undefined;
}

export function applyEvent(w: Work, e: AgentEvent): Work {
  switch (e.type) {
    case "run":
      return { ...w, runId: e.id, model: e.model, local: e.local };
    case "thinking":
      return e.text ? { ...w, thinking: [...w.thinking, e.text] } : w;
    case "todos":
      return { ...w, todos: e.items };
    case "task":
    case "subagent": {
      const i = w.steps.findIndex((s) => s.id === e.id);
      if (i >= 0) {
        const steps = w.steps.slice();
        steps[i] = { ...steps[i], status: e.status, summary: e.summary ?? steps[i].summary };
        return { ...w, steps };
      }
      const step: Step =
        e.type === "task"
          ? { id: e.id, kind: "task", label: TOOL_LABEL[e.name ?? ""] ?? (e.name ?? "Tool").replace(/_/g, " "), detail: argText(e.args), agent: e.agent, status: e.status, summary: e.summary }
          : { id: e.id, kind: "subagent", label: `Sub-agent · ${e.kind ?? "researcher"}`, detail: e.brief, status: e.status, summary: e.summary };
      return { ...w, steps: [...w.steps, step] };
    }
    case "token": {
      const last = w.drafts[w.drafts.length - 1];
      if (last && last.msg === e.msg) return { ...w, drafts: [...w.drafts.slice(0, -1), { ...last, text: last.text + e.text }] };
      return { ...w, drafts: [...w.drafts, { msg: e.msg, text: e.text }] };
    }
    case "step":
      return { ...w, working: [...w.working, String(e.msg)] };
    case "answer":
      return { ...w, answer: e.text };
    case "usage":
      return { ...w, usage: e, finished: true };
    case "error":
      return { ...w, error: e.message };
    case "done":
      return { ...w, finished: true };
  }
  return w;
}

/** The answer text so far: the final answer, else the live draft that is not working text. */
export function answerText(w: Work): string {
  if (w.answer) return w.answer;
  const live = [...w.drafts].reverse().find((d) => !w.working.includes(String(d.msg)));
  return live?.text ?? "";
}

/** Working text the supervisor wrote alongside tool calls counts as thinking too. */
function thoughts(w: Work) {
  const extra = w.drafts.filter((d) => w.working.includes(String(d.msg))).map((d) => d.text.trim()).filter(Boolean);
  return [...w.thinking, ...extra];
}

function Dot({ status }: { status: "pending" | "in_progress" | "completed" | "running" | "done" | "error" }) {
  if (status === "running" || status === "in_progress") return <CircularProgress size={10} thickness={6} sx={{ color: "var(--brand-indigo)", flexShrink: 0 }} />;
  if (status === "done" || status === "completed") return <CheckRoundedIcon sx={{ fontSize: 13, color: "var(--brand-indigo)", flexShrink: 0 }} />;
  if (status === "error") return <CloseRoundedIcon sx={{ fontSize: 13, color: "var(--brand-crimson, #b3261e)", flexShrink: 0 }} />;
  return <Box sx={{ width: 9, height: 9, border: "1px solid var(--text-muted)", borderRadius: "50%", flexShrink: 0 }} />;
}

const small = { fontSize: 11.5, lineHeight: 1.45 } as const;
const mono = { fontFamily: "var(--font-mono)", fontSize: 10.5, color: "var(--text-muted)" } as const;

export function AgentWork({ w }: { w: Work }) {
  const done = Boolean(w.answer || w.finished);
  const [open, setOpen] = useState<boolean | null>(null); // null: follow the run (open while working)
  const expanded = open ?? !done;
  const t = thoughts(w);
  const sources = w.steps.filter((s) => s.kind === "task" && s.status === "done").length;
  const subs = w.steps.filter((s) => s.kind === "subagent").length;
  const secs = w.usage ? `${(w.usage.ms / 1000).toFixed(1)}s` : null;
  const summary = done
    ? [`${w.steps.length} step${w.steps.length === 1 ? "" : "s"}`, `${sources} source${sources === 1 ? "" : "s"}`, subs ? `${subs} sub-agent${subs === 1 ? "" : "s"}` : null, secs, w.model]
        .filter(Boolean)
        .join(" · ")
    : w.todos.find((x) => x.status === "in_progress")?.content ?? (w.steps.length ? w.steps[w.steps.length - 1].label : "Thinking");
  if (!w.runId && !t.length && !w.todos.length && !w.steps.length) return null;

  return (
    <Box sx={{ border: "1px solid var(--border-subtle)", borderRadius: "4px", mb: 1, bgcolor: "var(--bg-muted)" }}>
      <ButtonBase
        onClick={() => setOpen(!expanded)}
        aria-expanded={expanded}
        sx={{ width: "100%", justifyContent: "flex-start", gap: 0.75, px: 1, py: 0.6, textAlign: "left" }}
      >
        {done ? <CheckRoundedIcon sx={{ fontSize: 13, color: "var(--brand-indigo)" }} /> : <CircularProgress size={10} thickness={6} sx={{ color: "var(--brand-indigo)" }} />}
        <Typography sx={{ ...small, fontWeight: 600 }}>{done ? "Worked" : "Working"}</Typography>
        <Typography sx={{ ...small, color: "text.secondary", flex: 1, minWidth: 0, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{summary}</Typography>
        <ExpandMoreRoundedIcon sx={{ fontSize: 16, transform: expanded ? "rotate(180deg)" : "none", transition: "transform .15s" }} />
      </ButtonBase>
      {expanded && (
        <Stack spacing={1} sx={{ px: 1.25, pb: 1.1, pt: 0.25, borderTop: "1px solid var(--border-subtle)" }}>
          {t.length > 0 && (
            <Box>
              <Typography sx={{ ...mono, mb: 0.25 }}>THINKING</Typography>
              {t.map((x, i) => (
                <Typography key={i} sx={{ ...small, fontStyle: "italic", color: "text.secondary" }}>{x}</Typography>
              ))}
            </Box>
          )}
          {w.todos.length > 0 && (
            <Box>
              <Typography sx={{ ...mono, mb: 0.25 }}>PLAN</Typography>
              <Stack spacing={0.35}>
                {w.todos.map((x, i) => (
                  <Stack key={i} direction="row" spacing={0.75} alignItems="center">
                    <Dot status={x.status} />
                    <Typography sx={{ ...small, textDecoration: x.status === "completed" ? "line-through" : "none", color: x.status === "completed" ? "text.secondary" : "text.primary" }}>{x.content}</Typography>
                  </Stack>
                ))}
              </Stack>
            </Box>
          )}
          {w.steps.length > 0 && (
            <Box>
              <Typography sx={{ ...mono, mb: 0.25 }}>STEPS</Typography>
              <Stack spacing={0.5}>
                {w.steps.map((s) => (
                  <Box key={s.id} sx={{ pl: s.agent && s.agent !== "supervisor" ? 1.5 : 0, borderLeft: s.agent && s.agent !== "supervisor" ? "1px solid var(--border-subtle)" : "none" }}>
                    <Stack direction="row" spacing={0.75} alignItems="center">
                      <Dot status={s.status} />
                      <Typography sx={{ ...small, fontWeight: s.kind === "subagent" ? 600 : 400 }}>{s.label}</Typography>
                    </Stack>
                    {s.detail && <Typography sx={{ ...mono, pl: 2.2 }}>{s.detail}</Typography>}
                    {s.summary && s.status !== "running" && (
                      <Typography sx={{ ...mono, pl: 2.2, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }} title={s.summary}>→ {s.summary}</Typography>
                    )}
                  </Box>
                ))}
              </Stack>
            </Box>
          )}
          {w.error && <Typography sx={{ ...small, color: "var(--brand-crimson, #b3261e)" }}>{w.error} Answering without the agent instead.</Typography>}
          {w.usage && (
            <Typography sx={mono}>
              {w.model} {w.local ? "· on-premise" : "· hosted"} · {w.usage.tokensIn + w.usage.tokensOut} tokens{w.usage.costUsd ? ` · $${w.usage.costUsd.toFixed(4)}` : ""}
            </Typography>
          )}
        </Stack>
      )}
    </Box>
  );
}
