import { useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Alert, Box, Button, Stack, Typography } from "@mui/material";
import { PageHeader } from "../../components/common/PageHeader";
import { ActivityTimeline } from "./ActivityTimeline";
import { unmatchedA, unmatchedB } from "./data";

type Txn = (typeof unmatchedA)[number];

export function ManualMatchPage() {
  const navigate = useNavigate();
  const [selectedA, setSelectedA] = useState<string[]>([]);
  const [selectedB, setSelectedB] = useState<string[]>([]);

  const aRows = unmatchedA.filter((row) => selectedA.includes(row.id));
  const bRows = unmatchedB.filter((row) => selectedB.includes(row.id));
  const totalA = aRows.reduce((sum, row) => sum + row.amount, 0);
  const totalB = bRows.reduce((sum, row) => sum + row.amount, 0);
  const difference = totalA - totalB;
  const variance = totalA === 0 ? 0 : Math.abs(difference) / totalA;
  const withinTolerance = variance <= 0.005;
  const matchType = `${aRows.length || 0}:${bRows.length || 0}`;

  const validation = useMemo(() => {
    if (!aRows.length || !bRows.length) {
      return "Select at least one transaction on each side.";
    }
    if (!withinTolerance) {
      return "Variance exceeds 0.5% tolerance policy.";
    }
    return "Within tolerance. Policy check passed. Exposure $91,050.";
  }, [aRows.length, bRows.length, withinTolerance]);

  function toggle(id: string, side: "A" | "B") {
    const setter = side === "A" ? setSelectedA : setSelectedB;
    setter((current) => (current.includes(id) ? current.filter((item) => item !== id) : [...current, id]));
  }

  function suggestMatch() {
    setSelectedA(["INV-4501"]);
    setSelectedB(["GL-8902", "GL-8903"]);
  }

  return (
    <>
      <PageHeader
        title="Manual Match Workbench"
        description="Build 1:1, 1:M, M:1, or M:M matches from unmatched items. Keyboard-selectable; no extra clicks to add."
        actions={
          <Button variant="outlined" onClick={suggestMatch}>
            Suggest Match
          </Button>
        }
      />

      <Box sx={{ display: "grid", gridTemplateColumns: { xs: "1fr", lg: "1fr 1.1fr 1fr" }, gap: 2.5 }}>
        <TxnPicker title="Unmatched A" rows={unmatchedA} selected={selectedA} onToggle={(id) => toggle(id, "A")} />

        <Box sx={{ p: 2, bgcolor: "background.paper", border: "1px solid", borderColor: "divider", borderRadius: 1 }}>
          <Typography variant="h6">Match builder</Typography>
          <Typography sx={{ fontSize: 12, color: "text.secondary", mb: 1.5 }}>
            Type {matchType.replace(":", " : ")} · click rows to add or remove
          </Typography>
          <Stack spacing={1} sx={{ mb: 2 }}>
            <Typography sx={{ fontSize: 12, fontWeight: 700 }}>A side</Typography>
            {aRows.map((row) => (
              <Typography key={row.id} sx={{ fontSize: 12 }}>
                {row.invoice} · {row.amount.toLocaleString()}
              </Typography>
            ))}
            <Typography sx={{ fontSize: 12, fontWeight: 700 }}>B side</Typography>
            {bRows.map((row) => (
              <Typography key={row.id} sx={{ fontSize: 12 }}>
                {row.invoice} · {row.amount.toLocaleString()}
              </Typography>
            ))}
          </Stack>
          <Stack spacing={0.5} sx={{ mb: 2 }}>
            <Metric label="A side total" value={totalA} />
            <Metric label="B side total" value={totalB} />
            <Metric label="Difference" value={difference} />
            <Typography sx={{ fontSize: 12 }}>Variance {(variance * 100).toFixed(2)}%</Typography>
          </Stack>
          <Alert severity={withinTolerance && aRows.length && bRows.length ? "success" : "warning"} sx={{ mb: 2 }}>
            {validation}
          </Alert>
          <Stack direction="row" spacing={1}>
            <Button
              variant="contained"
              disabled={!withinTolerance || !aRows.length || !bRows.length}
              onClick={() => navigate("/reconciliation/approvals")}
            >
              Save & submit approval
            </Button>
            <Button
              onClick={() => {
                setSelectedA([]);
                setSelectedB([]);
              }}
            >
              Clear
            </Button>
          </Stack>
        </Box>

        <TxnPicker title="Unmatched B" rows={unmatchedB} selected={selectedB} onToggle={(id) => toggle(id, "B")} />
      </Box>
      <ActivityTimeline />
    </>
  );
}

function Metric({ label, value }: { label: string; value: number }) {
  return (
    <Stack direction="row" justifyContent="space-between">
      <Typography sx={{ fontSize: 12 }}>{label}</Typography>
      <Typography sx={{ fontFamily: '"IBM Plex Sans", sans-serif', fontWeight: 700, fontSize: 12 }}>
        {value.toLocaleString()}
      </Typography>
    </Stack>
  );
}

function TxnPicker({
  title,
  rows,
  selected,
  onToggle,
}: {
  title: string;
  rows: Txn[];
  selected: string[];
  onToggle: (id: string) => void;
}) {
  return (
    <Box sx={{ bgcolor: "background.paper", border: "1px solid", borderColor: "divider", borderRadius: 1 }}>
      <Typography variant="h6" sx={{ p: 1.5, pb: 1 }}>
        {title}
      </Typography>
      {rows.map((row) => (
        <Box
          key={row.id}
          role="checkbox"
          aria-checked={selected.includes(row.id)}
          tabIndex={0}
          onClick={() => onToggle(row.id)}
          onKeyDown={(event) => {
            if (event.key === "Enter" || event.key === " ") {
              event.preventDefault();
              onToggle(row.id);
            }
          }}
          sx={{
            px: 1.5,
            py: 1,
            cursor: "pointer",
            borderTop: "1px solid",
            borderColor: "divider",
            bgcolor: selected.includes(row.id) ? "var(--blue-soft)" : "transparent",
          }}
        >
          <Stack direction="row" justifyContent="space-between">
            <Typography sx={{ fontWeight: 700, fontSize: 12 }}>{row.invoice}</Typography>
            <Typography sx={{ fontFamily: '"IBM Plex Sans", sans-serif', fontSize: 12 }}>{row.amount.toLocaleString()}</Typography>
          </Stack>
          <Typography sx={{ fontSize: 11, color: "text.secondary" }}>
            {row.entity} · {row.date}
          </Typography>
        </Box>
      ))}
    </Box>
  );
}
