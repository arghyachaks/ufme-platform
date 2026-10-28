import { useEffect, useRef, useState } from "react";
import { Box, Button, Chip, CircularProgress, Stack, TextField, Typography } from "@mui/material";
import AutoAwesomeOutlinedIcon from "@mui/icons-material/AutoAwesomeOutlined";
import { api } from "../../api/services";
import { useQuery } from "../../api/useQuery";
import type { ChatMessage } from "../../api/types";
import { Panel } from "../../components/common/Panel";
import { Page, glass } from "../../components/common/Blocks";

const tidy = (t: string) =>
  t
    .replace(/\$\\leftrightarrow\$|\\leftrightarrow/g, "↔")
    .replace(/\*\*(.+?)\*\*/g, "$1")
    .replace(/^\s*[*-]\s+/gm, "• ");

export function CopilotPage() {
  const { data, loading } = useQuery(api.ai.copilotSeed);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [thinking, setThinking] = useState(false);
  const end = useRef<HTMLDivElement>(null);
  useEffect(() => { if (data) setMessages(data.messages); }, [data]);
  useEffect(() => { end.current?.scrollIntoView({ behavior: "smooth", block: "nearest" }); }, [messages, thinking]);

  /** Streams from ufme Assist (the private on-premise model), falling back to standard answers when it's off. */
  const send = async (text: string) => {
    if (!text.trim() || thinking) return;
    const history = messages.map((m) => ({ role: m.role, content: m.text }));
    setMessages((m) => [...m, { role: "user", text }, { role: "assistant", text: "" }]);
    setInput("");
    setThinking(true);
    const append = (t: string) =>
      setMessages((m) => {
        const last = m[m.length - 1];
        return [...m.slice(0, -1), { ...last, text: last.text + t }];
      });
    try {
      await api.ai.assist({ prompt: text, history, page: "/ai/copilot", onDelta: append });
    } catch {
      append("Sorry, I couldn't reach the assistant just now. Please try again.");
    } finally {
      setMessages((m) => {
        const last = m[m.length - 1];
        const refs = Array.from(new Set(last.text.match(/\b(?:EX|CS|MT|AP|RUN|JE)-\d+\b/g) ?? []));
        return [...m.slice(0, -1), { ...last, text: tidy(last.text), refs }];
      });
      setThinking(false);
    }
  };

  return (
    <Page title="Assistant" description="Ask about matches, exceptions, and close status. Answers cite the records they're based on; actions always go through normal approval." loading={loading}>
      <Box sx={{ display: "grid", gridTemplateColumns: { xs: "1fr", lg: "1fr 300px" }, gap: 2.5 }}>
        <Box sx={{ ...glass, display: "flex", flexDirection: "column", height: 560 }}>
          <Box sx={{ flex: 1, overflowY: "auto", p: 2 }}>
            <Stack spacing={1.5}>
              {messages.filter((m) => m.text || !thinking).map((m, i) => (
                <Box key={i} sx={{ alignSelf: m.role === "user" ? "flex-end" : "flex-start", maxWidth: "80%" }}>
                  <Box sx={{ px: 1.75, py: 1.25, borderRadius: 2, bgcolor: m.role === "user" ? "primary.main" : "var(--indigo-soft)", color: m.role === "user" ? "#fff" : "text.primary" }}>
                    {m.role === "assistant" ? <AutoAwesomeOutlinedIcon sx={{ fontSize: 14, mr: 0.75, verticalAlign: "-2px", color: "primary.main" }} /> : null}
                    <Typography component="span" sx={{ fontSize: 13, whiteSpace: "pre-wrap" }}>{m.text}</Typography>
                  </Box>
                  {m.refs?.length ? (
                    <Stack direction="row" spacing={0.5} sx={{ mt: 0.5 }} flexWrap="wrap" useFlexGap>
                      {m.refs.map((r) => <Chip key={r} size="small" variant="outlined" label={r} />)}
                    </Stack>
                  ) : null}
                </Box>
              ))}
              {thinking ? <Stack direction="row" spacing={1} alignItems="center"><CircularProgress size={14} /><Typography sx={{ fontSize: 12, color: "text.secondary" }}>Looking through matches and cases…</Typography></Stack> : null}
              <div ref={end} />
            </Stack>
          </Box>
          <Stack direction="row" spacing={1} sx={{ p: 1.5, borderTop: "1px solid", borderColor: "divider" }}>
            <TextField fullWidth size="small" placeholder="Ask about a match, case, entity, or the close…" value={input}
              onChange={(e) => setInput(e.target.value)} onKeyDown={(e) => e.key === "Enter" && send(input)} />
            <Button variant="contained" onClick={() => send(input)} disabled={!input.trim() || thinking}>Send</Button>
          </Stack>
        </Box>
        <Stack spacing={2.5}>
          <Panel title="Try asking">
            <Stack spacing={1}>
              {data?.prompts.map((p) => <Button key={p} size="small" variant="outlined" sx={{ justifyContent: "flex-start", textAlign: "left" }} onClick={() => send(p)}>{p}</Button>)}
            </Stack>
          </Panel>
          <Panel title="Guardrails">
            {["Runs privately on your own hardware", "Answers only from your ufme data", "Quotes the record IDs it used", "Can't approve or change anything", "Every question is logged to the audit trail"].map((g) => (
              <Typography key={g} sx={{ fontSize: 12, mb: 0.5 }}>• {g}</Typography>
            ))}
          </Panel>
        </Stack>
      </Box>
    </Page>
  );
}
