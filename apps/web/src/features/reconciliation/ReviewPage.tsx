import { useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { Box, Button, Stack, Typography } from "@mui/material";
import { PageHeader } from "../../components/common/PageHeader";
import { StatusPill } from "../../components/common/Panel";
import { ActivityTimeline } from "./ActivityTimeline";
import { sideA, sideB, suggestedMatch } from "./data";

export function ReviewPage() {
  const [params] = useSearchParams();
  const navigate = useNavigate();
  const [index, setIndex] = useState(0);
  const left = sideA[index] ?? sideA[0];
  const runId = params.get("run") ?? "IC-2026-08-17";

  return (
    <>
      <PageHeader
        title="Review Workbench"
        description={`Run ${runId}. Approve, reject, or escalate suggested matches with full explainability.`}
        actions={
          <Stack direction="row" spacing={1}>
            <Button size="small" disabled={index === 0} onClick={() => setIndex((value) => value - 1)}>
              Previous
            </Button>
            <Button size="small" disabled={index === sideA.length - 1} onClick={() => setIndex((value) => value + 1)}>
              Next
            </Button>
          </Stack>
        }
      />

      <Box sx={{ display: "grid", gridTemplateColumns: { xs: "1fr", lg: "1fr 1.2fr 1fr" }, gap: 2.5, minHeight: 420 }}>
        <TxnList title="Transaction Set A" rows={sideA} selectedId={left.id} onSelect={(id) => setIndex(sideA.findIndex((row) => row.id === id))} />

        <Box sx={{ p: 2, bgcolor: "background.paper", border: "1px solid", borderColor: "divider", borderRadius: 1 }}>
          <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ mb: 1 }}>
            <Typography variant="h6">Suggested match</Typography>
            <StatusPill label={suggestedMatch.type} tone="ok" />
          </Stack>
          <Typography sx={{ fontFamily: '"IBM Plex Sans", sans-serif', fontSize: 22, fontWeight: 700 }}>
            {suggestedMatch.confidence}
          </Typography>
          <Typography sx={{ fontSize: 12, color: "text.secondary", mb: 1.5 }}>Confidence · {suggestedMatch.rule}</Typography>
          <Typography sx={{ fontSize: 12, fontWeight: 700, mb: 0.75 }}>Why matched</Typography>
          <Stack spacing={0.5} sx={{ mb: 1.5 }}>
            {suggestedMatch.why.map((item) => (
              <Typography key={item} sx={{ fontSize: 12 }}>
                • {item}
              </Typography>
            ))}
          </Stack>
          <Typography sx={{ fontSize: 12, color: "text.secondary", mb: 2 }}>{suggestedMatch.historical}</Typography>
          <Stack direction="row" spacing={1} flexWrap="wrap">
            <Button variant="contained" color="success">
              Approve
            </Button>
            <Button variant="outlined" color="error">
              Reject
            </Button>
            <Button variant="outlined" onClick={() => navigate("/reconciliation/approvals")}>
              Escalate
            </Button>
            <Button variant="text" onClick={() => navigate("/reconciliation/manual-match")}>
              Manual match
            </Button>
          </Stack>
        </Box>

        <TxnList title="Transaction Set B" rows={sideB} selectedId={sideB[0]?.id} />
      </Box>
      <ActivityTimeline />
    </>
  );
}

function TxnList({
  title,
  rows,
  selectedId,
  onSelect,
}: {
  title: string;
  rows: Array<{ id: string; invoice: string; amount: number; date: string; entity: string; status?: string; score?: number }>;
  selectedId?: string;
  onSelect?: (id: string) => void;
}) {
  return (
    <Box sx={{ bgcolor: "background.paper", border: "1px solid", borderColor: "divider", borderRadius: 1, overflow: "auto" }}>
      <Typography variant="h6" sx={{ p: 1.5, pb: 1 }}>
        {title}
      </Typography>
      {rows.map((row) => {
        const selected = row.id === selectedId;
        return (
          <Box
            key={row.id}
            role="button"
            tabIndex={0}
            onClick={() => onSelect?.(row.id)}
            onKeyDown={(event) => {
              if (event.key === "Enter" || event.key === " ") {
                onSelect?.(row.id);
              }
            }}
            sx={{
              px: 1.5,
              py: 1,
              cursor: onSelect ? "pointer" : "default",
              borderTop: "1px solid",
              borderColor: "divider",
              bgcolor: selected ? "var(--indigo-soft)" : "transparent",
            }}
          >
            <Stack direction="row" justifyContent="space-between">
              <Typography sx={{ fontWeight: 700, fontSize: 12 }}>{row.invoice}</Typography>
              <Typography sx={{ fontFamily: '"IBM Plex Sans", sans-serif', fontSize: 12, fontWeight: 700 }}>
                {row.amount.toLocaleString()}
              </Typography>
            </Stack>
            <Typography sx={{ fontSize: 11, color: "text.secondary" }}>
              {row.entity} · {row.date}
              {row.score ? ` · score ${row.score}` : ""}
              {row.status ? ` · ${row.status}` : ""}
            </Typography>
          </Box>
        );
      })}
    </Box>
  );
}
