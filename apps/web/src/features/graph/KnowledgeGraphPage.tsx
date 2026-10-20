import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { Box, Button, Chip, Stack, Typography } from "@mui/material";
import { api } from "../../api/services";
import { useQuery } from "../../api/useQuery";
import type { GraphNode } from "../../api/types";
import { Panel } from "../../components/common/Panel";
import { KeyValue, Page, glass } from "../../components/common/Blocks";

const kindColor: Record<GraphNode["kind"], string> = { Entity: "var(--brand-indigo)", Counterparty: "var(--brand-blue)", Account: "var(--text-muted)", Transaction: "var(--brand-emerald)", Case: "var(--brand-crimson)" };
const riskRing = { ok: "var(--brand-emerald)", warn: "var(--brand-amber)", crit: "var(--brand-crimson)" };

export function KnowledgeGraphPage() {
  const { data, loading } = useQuery(api.graph.get);
  const [sel, setSel] = useState<string>("US01");
  const navigate = useNavigate();
  const node = data?.nodes.find((n) => n.id === sel);
  const linked = data?.edges.filter((e) => e.from === sel || e.to === sel) ?? [];
  const isLinked = (id: string) => id === sel || linked.some((e) => e.from === id || e.to === id);

  return (
    <Page title="Knowledge graph" description="How entities, counterparties, accounts, transactions, and cases connect — used for candidate generation and investigation." loading={loading}>
      {data ? (
        <Box sx={{ display: "grid", gridTemplateColumns: { xs: "1fr", lg: "1fr 300px" }, gap: 2.5 }}>
          <Box sx={{ ...glass, p: 1 }}>
            <svg viewBox="0 0 820 380" width="100%" style={{ display: "block" }}>
              {data.edges.map((e) => {
                const a = data.nodes.find((n) => n.id === e.from)!;
                const b = data.nodes.find((n) => n.id === e.to)!;
                const on = e.from === sel || e.to === sel;
                return (
                  <g key={e.from + e.to} opacity={on ? 1 : 0.25}>
                    <line x1={a.x} y1={a.y} x2={b.x} y2={b.y} stroke="currentColor" strokeWidth={on ? 2 : 1} style={{ color: "var(--text-secondary)" }} />
                    <text x={(a.x + b.x) / 2} y={(a.y + b.y) / 2 - 4} fontSize={10} textAnchor="middle" fill="var(--text-secondary)">{e.label}</text>
                  </g>
                );
              })}
              {data.nodes.map((n) => (
                <g key={n.id} onClick={() => setSel(n.id)} style={{ cursor: "pointer" }} opacity={isLinked(n.id) ? 1 : 0.4}>
                  <circle cx={n.x} cy={n.y} r={n.id === sel ? 24 : 18} fill={kindColor[n.kind]} fillOpacity={0.9} stroke={n.risk ? riskRing[n.risk] : "none"} strokeWidth={3} />
                  <text x={n.x} y={n.y + 36} fontSize={11} fontWeight={600} textAnchor="middle" fill="var(--text-primary)">{n.label}</text>
                </g>
              ))}
            </svg>
            <Stack direction="row" spacing={1} sx={{ px: 1, pb: 1 }} flexWrap="wrap" useFlexGap>
              {Object.entries(kindColor).map(([k, c]) => <Chip key={k} size="small" label={k} sx={{ bgcolor: c, color: "#fff" }} />)}
            </Stack>
          </Box>
          {node ? (
            <Panel title={node.label}>
              <KeyValue label="Type" value={node.kind} />
              <KeyValue label="Risk" value={node.risk ?? "—"} />
              <KeyValue label="Connections" value={linked.length} />
              <Typography variant="subtitle2" sx={{ mt: 2, mb: 1 }}>Relationships</Typography>
              {linked.map((e) => (
                <Typography key={e.from + e.to} sx={{ fontSize: 12, mb: 0.5 }}>
                  {e.from === sel ? "→" : "←"} <b>{e.from === sel ? e.to : e.from}</b> · {e.label}
                </Typography>
              ))}
              {node.kind === "Entity" ? <Button size="small" sx={{ mt: 1.5 }} onClick={() => navigate("/exceptions")}>Entity exceptions →</Button> : null}
              {node.kind === "Case" ? <Button size="small" sx={{ mt: 1.5 }} onClick={() => navigate("/exceptions/cases")}>Open case →</Button> : null}
            </Panel>
          ) : null}
        </Box>
      ) : null}
    </Page>
  );
}
