import { useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Alert, Box, Button, Checkbox, Drawer, Stack, Typography } from "@mui/material";
import { PageHeader } from "../../components/common/PageHeader";
import { StatusPill } from "../../components/common/Panel";
import { ActivityTimeline } from "./ActivityTimeline";
import { workspaceApi, type ReconData } from "../../api/services";
import { useQuery } from "../../api/useQuery";
import { PageSkeleton } from "../../components/common/Blocks";

type Txn = (ReconData["unmatchedA"])[number];

function matchTypeLabel(aCount: number, bCount: number) {
  if (!aCount || !bCount) return "Select both sides";
  if (aCount === 1 && bCount === 1) return "1:1 Match";
  if (aCount === 1 && bCount > 1) return "1:M Match";
  if (aCount > 1 && bCount === 1) return "M:1 Match";
  return "M:M Match";
}

export function ManualMatchPage() {
  const { data } = useQuery(workspaceApi.recon);
  return data ? <ManualMatchPageView d={data} /> : <PageSkeleton />;
}

function ManualMatchPageView({ d }: { d: ReconData }) {
  const { matchTolerancePolicy, manualSuggestWhy, unmatchedA, unmatchedB } = d;
  const navigate = useNavigate();
  const [selectedA, setSelectedA] = useState<string[]>([]);
  const [selectedB, setSelectedB] = useState<string[]>([]);
  const [suggested, setSuggested] = useState(false);
  const [preview, setPreview] = useState<{ title: string; files: string[] } | null>(null);

  const aRows = unmatchedA.filter((row) => selectedA.includes(row.id));
  const bRows = unmatchedB.filter((row) => selectedB.includes(row.id));
  const totalA = aRows.reduce((sum, row) => sum + row.amount, 0);
  const totalB = bRows.reduce((sum, row) => sum + row.amount, 0);
  const difference = totalA - totalB;
  const variance = totalA === 0 ? 0 : Math.abs(difference) / totalA;
  const withinTolerance = variance <= matchTolerancePolicy;
  const typeLabel = matchTypeLabel(aRows.length, bRows.length);
  const policyReady = Boolean(aRows.length && bRows.length && withinTolerance);

  const validation = useMemo(() => {
    if (!aRows.length || !bRows.length) {
      return "Select at least one transaction on each side.";
    }
    if (!withinTolerance) {
      return "Variance exceeds 0.5% tolerance policy.";
    }
    return "Within policy. Ready to submit or convert remaining items to exceptions.";
  }, [aRows.length, bRows.length, withinTolerance]);

  function toggle(id: string, side: "A" | "B") {
    const setter = side === "A" ? setSelectedA : setSelectedB;
    setter((current) => (current.includes(id) ? current.filter((item) => item !== id) : [...current, id]));
  }

  function suggestMatch() {
    setSelectedA(["INV-4501"]);
    setSelectedB(["GL-8902", "GL-8903"]);
    setSuggested(true);
  }

  return (
    <>
      <PageHeader
        title="Manual Match Workbench"
        description="Build 1:1, 1:M, M:1, or M:M matches from unmatched items. Review first, then use AI suggestion."
        actions={
          <Stack direction="row" spacing={1}>
            <Button variant="outlined" onClick={() => navigate("/exceptions")}>
              Open exceptions
            </Button>
            <Button variant="outlined" onClick={suggestMatch}>
              Suggest Match
            </Button>
          </Stack>
        }
      />

      <Box sx={{ display: "grid", gridTemplateColumns: { xs: "1fr", lg: "1fr 1.15fr 1fr" }, gap: 2.5 }}>
        <TxnPicker
          title="Unmatched A"
          rows={unmatchedA}
          selected={selectedA}
          runningTotal={totalA}
          onToggle={(id) => toggle(id, "A")}
          onPreview={(row) => setPreview({ title: row.invoice, files: row.attachments })}
        />

        <Box sx={{ p: 2, bgcolor: "var(--glass-bg)", backdropFilter: "blur(18px) saturate(150%)", border: "1px solid", borderColor: "divider", borderRadius: 1 }}>
          <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ mb: 1.5 }}>
            <Typography variant="h6">Match builder</Typography>
            <Box
              sx={{
                px: 1.25,
                py: 0.5,
                borderRadius: 1,
                bgcolor: "primary.main",
                color: "primary.contrastText",
                fontSize: 14,
                fontWeight: 800,
              }}
            >
              {typeLabel}
            </Box>
          </Stack>

          <Box sx={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 1, mb: 2 }}>
            <PolicyStat label="Tolerance allowed" value="0.5%" />
            <PolicyStat label="Current variance" value={`${(variance * 100).toFixed(2)}%`} />
            <Box sx={{ p: 1, border: "1px solid", borderColor: "divider", borderRadius: 1 }}>
              <Typography sx={{ fontSize: 10, color: "text.secondary", textTransform: "uppercase" }}>Status</Typography>
              <Box sx={{ mt: 0.5 }}>
                <StatusPill label={policyReady ? "Within Policy" : "Out of Policy"} tone={policyReady ? "ok" : "warn"} />
              </Box>
            </Box>
          </Box>

          <Stack spacing={1} sx={{ mb: 2 }}>
            <Typography sx={{ fontSize: 12, fontWeight: 700 }}>A side · {aRows.length} selected · {totalA.toLocaleString()}</Typography>
            {aRows.map((row) => (
              <Typography key={row.id} sx={{ fontSize: 12 }}>
                {row.invoice} · {row.amount.toLocaleString()}
              </Typography>
            ))}
            <Typography sx={{ fontSize: 12, fontWeight: 700 }}>B side · {bRows.length} selected · {totalB.toLocaleString()}</Typography>
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
          </Stack>

          {suggested && (
            <Box sx={{ p: 1.25, mb: 2, bgcolor: "var(--indigo-soft)", borderRadius: 1 }}>
              <Typography sx={{ fontSize: 12, fontWeight: 700, mb: 0.5 }}>Why suggested</Typography>
              {manualSuggestWhy.map((item) => (
                <Typography key={item} sx={{ fontSize: 12 }}>
                  • {item}
                </Typography>
              ))}
            </Box>
          )}

          <Alert severity={policyReady ? "success" : "warning"} sx={{ mb: 2 }}>
            {validation}
          </Alert>
          <Stack direction="row" spacing={1} flexWrap="wrap">
            <Button variant="contained" disabled={!policyReady} onClick={() => navigate("/reconciliation/approvals")}>
              Save & submit approval
            </Button>
            <Button variant="outlined" color="warning" onClick={() => navigate("/exceptions/cases")}>
              Create exception
            </Button>
            <Button variant="text" onClick={() => navigate("/exceptions/cases")}>
              Open case
            </Button>
            <Button
              onClick={() => {
                setSelectedA([]);
                setSelectedB([]);
                setSuggested(false);
              }}
            >
              Clear
            </Button>
          </Stack>
        </Box>

        <TxnPicker
          title="Unmatched B"
          rows={unmatchedB}
          selected={selectedB}
          runningTotal={totalB}
          onToggle={(id) => toggle(id, "B")}
          onPreview={(row) => setPreview({ title: row.invoice, files: row.attachments })}
        />
      </Box>
      <ActivityTimeline />

      <Drawer anchor="right" open={Boolean(preview)} onClose={() => setPreview(null)}>
        <Box sx={{ width: { xs: 320, sm: 400 }, p: 2.5 }}>
          <Typography variant="h6" sx={{ mb: 1 }}>
            Documents · {preview?.title}
          </Typography>
          {preview?.files.map((file) => (
            <Box key={file} sx={{ p: 1.25, mb: 1, border: "1px solid", borderColor: "divider", borderRadius: 1 }}>
              <Typography sx={{ fontSize: 13, fontWeight: 700 }}>{file}</Typography>
              <Typography sx={{ fontSize: 11, color: "text.secondary" }}>Preview stub · invoice / GL / journal</Typography>
            </Box>
          ))}
        </Box>
      </Drawer>
    </>
  );
}

function PolicyStat({ label, value }: { label: string; value: string }) {
  return (
    <Box sx={{ p: 1, border: "1px solid", borderColor: "divider", borderRadius: 1 }}>
      <Typography sx={{ fontSize: 10, color: "text.secondary", textTransform: "uppercase" }}>{label}</Typography>
      <Typography sx={{ fontFamily: '"IBM Plex Sans", sans-serif', fontWeight: 800, fontSize: 16 }}>{value}</Typography>
    </Box>
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
  runningTotal,
  onToggle,
  onPreview,
}: {
  title: string;
  rows: Txn[];
  selected: string[];
  runningTotal: number;
  onToggle: (id: string) => void;
  onPreview: (row: Txn) => void;
}) {
  return (
    <Box sx={{ bgcolor: "var(--glass-bg)", backdropFilter: "blur(18px) saturate(150%)", border: "1px solid", borderColor: "divider", borderRadius: 1 }}>
      <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ p: 1.5, pb: 1 }}>
        <Typography variant="h6">{title}</Typography>
        <Typography sx={{ fontSize: 12, fontWeight: 700 }}>{selected.length} · {runningTotal.toLocaleString()}</Typography>
      </Stack>
      {rows.map((row) => {
        const checked = selected.includes(row.id);
        return (
          <Box
            key={row.id}
            role="checkbox"
            aria-checked={checked}
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
              bgcolor: checked ? "var(--indigo-soft)" : "transparent",
              boxShadow: checked ? "inset 3px 0 0 var(--brand-indigo, #4f46e5)" : "none",
            }}
          >
            <Stack direction="row" spacing={1} alignItems="flex-start">
              <Checkbox size="small" checked={checked} sx={{ p: 0, mt: 0.2 }} tabIndex={-1} />
              <Box sx={{ flex: 1 }}>
                <Stack direction="row" justifyContent="space-between">
                  <Typography sx={{ fontWeight: 700, fontSize: 12 }}>{row.invoice}</Typography>
                  <Typography sx={{ fontFamily: '"IBM Plex Sans", sans-serif', fontSize: 12, fontWeight: 700 }}>
                    {row.amount.toLocaleString()}
                  </Typography>
                </Stack>
                <Stack direction="row" spacing={0.75} alignItems="center" sx={{ mt: 0.35 }}>
                  <Typography sx={{ fontSize: 11, color: "text.secondary" }}>
                    {row.entity} · {row.date}
                  </Typography>
                  <StatusPill
                    label={row.exceptionRisk}
                    tone={row.exceptionRisk === "High" ? "crit" : row.exceptionRisk === "Medium" ? "warn" : "ok"}
                  />
                </Stack>
                <Button
                  size="small"
                  sx={{ px: 0, mt: 0.25 }}
                  onClick={(event) => {
                    event.stopPropagation();
                    onPreview(row);
                  }}
                >
                  Documents
                </Button>
              </Box>
            </Stack>
          </Box>
        );
      })}
    </Box>
  );
}
