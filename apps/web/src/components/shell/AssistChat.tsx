import { useEffect, useRef, useState } from "react";
import { Box, IconButton, InputBase, Stack, Typography } from "@mui/material";
import ArrowUpwardRoundedIcon from "@mui/icons-material/ArrowUpwardRounded";
import StopRoundedIcon from "@mui/icons-material/StopRounded";
import { api, type AssistStatus, type AssistTurn } from "../../api/services";

/** Small models sometimes slip into markdown/LaTeX; show clean business text regardless. */
function tidy(t: string) {
  return t
    .replace(/\$\\leftrightarrow\$|\\leftrightarrow/g, "↔")
    .replace(/\$\\rightarrow\$|\\rightarrow/g, "→")
    .replace(/\*\*(.+?)\*\*/g, "$1")
    .replace(/^\s*[*-]\s+/gm, "• ");
}

type Msg = { role: "user" | "assistant"; text: string; pending?: boolean };

/** Live status chip: green when the private on-premise model is loaded, amber when using standard answers. */
export function AssistStatusChip() {
  const [st, setSt] = useState<AssistStatus | null>(null);
  useEffect(() => {
    let alive = true;
    const load = () => api.ai.assistStatus().then((s) => alive && setSt(s)).catch(() => alive && setSt({ online: false, model: "" }));
    load();
    const t = setInterval(load, 30_000);
    return () => {
      alive = false;
      clearInterval(t);
    };
  }, []);
  const online = Boolean(st?.online);
  return (
    <Stack
      direction="row"
      alignItems="center"
      spacing={0.6}
      title={online ? "Answers are generated privately on your own hardware. No data leaves your network." : "The private model is not running; showing standard answers."}
      sx={{
        fontSize: 10.5,
        fontFamily: "var(--font-mono)",
        px: 0.9,
        py: 0.3,
        borderRadius: "5px",
        bgcolor: online ? "var(--indigo-soft)" : "var(--amber-soft)",
        color: online ? "var(--brand-indigo)" : "var(--brand-amber)",
      }}
    >
      <Box className={online ? "status-dot" : undefined} sx={{ width: 6, height: 6, borderRadius: "50%", bgcolor: "currentColor" }} />
      <span>{st === null ? "CONNECTING" : online ? "PRIVATE · ON-PREMISE" : "STANDARD ANSWERS"}</span>
    </Stack>
  );
}

export function AssistChat({ seed, page, placeholder }: { seed: Msg[]; page: string; placeholder: string }) {
  const [msgs, setMsgs] = useState<Msg[]>(seed);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const abort = useRef<AbortController | null>(null);
  const end = useRef<HTMLDivElement>(null);

  useEffect(() => {
    end.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [msgs]);

  async function send() {
    const prompt = input.trim();
    if (!prompt || busy) return;
    const history: AssistTurn[] = msgs.filter((m) => !m.pending).map((m) => ({ role: m.role, content: m.text }));
    setInput("");
    setBusy(true);
    setMsgs((m) => [...m, { role: "user", text: prompt }, { role: "assistant", text: "", pending: true }]);
    const ctrl = new AbortController();
    abort.current = ctrl;
    const append = (t: string) =>
      setMsgs((m) => {
        const last = m[m.length - 1];
        return [...m.slice(0, -1), { ...last, text: last.text + t }];
      });
    try {
      await api.ai.assist({ prompt, history, page, onDelta: append, signal: ctrl.signal });
    } catch {
      if (!ctrl.signal.aborted) append("Sorry, I couldn't reach the assistant just now. Please try again.");
    } finally {
      setMsgs((m) => [...m.slice(0, -1), { ...m[m.length - 1], pending: false }]);
      setBusy(false);
    }
  }

  return (
    <>
      <Stack spacing={1.25} sx={{ flex: 1, overflow: "auto", py: 1.75 }}>
        {msgs.map((message, index) => (
          <Box
            key={index}
            className="assist-msg"
            sx={{
              px: 1.5,
              py: 1.1,
              borderRadius: message.role === "user" ? "10px 10px 2px 10px" : "10px 10px 10px 2px",
              fontSize: 12.5,
              lineHeight: 1.55,
              maxWidth: "92%",
              whiteSpace: "pre-wrap",
              alignSelf: message.role === "user" ? "flex-end" : "flex-start",
              bgcolor: message.role === "user" ? "var(--bg-muted)" : "transparent",
              border: message.role === "user" ? "1px solid var(--border-subtle)" : "1px solid color-mix(in srgb, var(--brand-indigo) 22%, transparent)",
              color: "text.primary",
            }}
          >
            {message.role === "assistant" ? tidy(message.text) : message.text}
            {message.pending && !message.text && (
              <Box component="span" className="typing"><i /><i /><i /></Box>
            )}
            {message.pending && message.text && <Box component="span" className="caret" />}
          </Box>
        ))}
        <div ref={end} />
      </Stack>

      <Box sx={{ pt: 1.5, borderTop: "1px solid", borderColor: "divider" }}>
        <Stack
          direction="row"
          alignItems="flex-end"
          sx={{
            bgcolor: "var(--bg-muted)",
            border: "1px solid var(--border-subtle)",
            borderRadius: "10px",
            pl: 1.5,
            pr: 0.5,
            py: 0.5,
            "&:focus-within": { borderColor: "primary.main", boxShadow: "0 0 0 3px var(--indigo-soft)" },
          }}
        >
          <InputBase
            fullWidth
            multiline
            maxRows={5}
            value={input}
            placeholder={placeholder}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                void send();
              }
            }}
            sx={{ fontSize: 12.5, py: 0.6 }}
          />
          <IconButton
            size="small"
            aria-label={busy ? "Stop" : "Send"}
            onClick={() => (busy ? abort.current?.abort() : void send())}
            disabled={!busy && !input.trim()}
            sx={{ bgcolor: "primary.main", color: "primary.contrastText", width: 28, height: 28, "&:hover": { bgcolor: "primary.main", filter: "brightness(1.1)" }, "&.Mui-disabled": { bgcolor: "var(--border-strong)", color: "var(--text-muted)" } }}
          >
            {busy ? <StopRoundedIcon sx={{ fontSize: 16 }} /> : <ArrowUpwardRoundedIcon sx={{ fontSize: 16 }} />}
          </IconButton>
        </Stack>
        <Typography sx={{ fontSize: 10, color: "var(--text-muted)", mt: 0.75, textAlign: "center" }}>
          Suggestions only. Every action still goes through approval.
        </Typography>
      </Box>
    </>
  );
}
