import { useEffect, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import {
  Box,
  Button,
  Checkbox,
  Drawer,
  LinearProgress,
  Snackbar,
  Stack,
  Typography,
} from "@mui/material";
import { PageHeader } from "../../components/common/PageHeader";
import { StatusPill } from "../../components/common/Panel";
import { ActivityTimeline } from "./ActivityTimeline";
import { ReconRecoBar } from "./ReconLayout";
import { workspaceApi, type ReconData } from "../../api/services";
import { useQuery } from "../../api/useQuery";
import { PageSkeleton } from "../../components/common/Blocks";

const matchTypes = ["1:1", "1:M", "M:1", "M:M"] as const;

type SideARow = (ReconData["sideA"])[number];

const materialityTone: Record<string, "ok" | "warn" | "crit"> = {
  High: "crit",
  Medium: "warn",
  Low: "ok",
};

export function ReviewPage() {
  const { data } = useQuery(workspaceApi.recon);
  return data ? <ReviewPageView d={data} /> : <PageSkeleton />;
}

function ReviewPageView({ d }: { d: ReconData }) {
  const { sideA, sideB, suggestedMatch } = d;
  const [params] = useSearchParams();
  const navigate = useNavigate();
  const [index, setIndex] = useState(0);
  const [selectedIds, setSelectedIds] = useState<string[]>([]);
  const [queueSelected, setQueueSelected] = useState(false);
  const [drawerRow, setDrawerRow] = useState<SideARow | null>(null);
  const [toast, setToast] = useState("");
  const left = sideA[index] ?? sideA[0];
  const runId = params.get("run") ?? "IC-2026-08-17";
  const selectedCount = queueSelected ? suggestedMatch.queueSize : selectedIds.length;
  const allVisibleSelected = sideA.every((row) => selectedIds.includes(row.id));

  const goNext = () => setIndex((value) => Math.min(sideA.length - 1, value + 1));

  useEffect(() => {
    const onKey = (event: KeyboardEvent) => {
      const target = event.target as HTMLElement | null;
      if (target && ["INPUT", "TEXTAREA", "SELECT"].includes(target.tagName)) return;
      const key = event.key.toLowerCase();
      if (key === "a") {
        setToast(`Approved ${left.id}`);
        goNext();
      }
      if (key === "r") setToast(`Rejected ${left.id}`);
      if (key === "e") navigate("/reconciliation/approvals");
      if (key === "n") goNext();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [left.id, navigate]);

  const toggleSelect = (id: string) => {
    setQueueSelected(false);
    setSelectedIds((current) => (current.includes(id) ? current.filter((item) => item !== id) : [...current, id]));
  };

  const batch = (action: string) => {
    if (!selectedCount) return;
    setToast(`${action} ${selectedCount} matches`);
    setSelectedIds([]);
    setQueueSelected(false);
  };

  return (
    <>
      <PageHeader
        title="Review Workbench"
        description={`Run ${runId}. Shortcuts: A approve · R reject · E escalate · N next. Queue ${suggestedMatch.queueSize}.`}
        actions={
          <Stack direction="row" spacing={1} alignItems="center">
            <StatusPill label={`SLA: ${left.slaRemaining}`} tone={left.slaRemaining.startsWith("6h") ? "crit" : "warn"} />
            <Button size="small" disabled={index === 0} onClick={() => setIndex((value) => value - 1)}>
              Previous
            </Button>
            <Button size="small" disabled={index === sideA.length - 1} onClick={goNext}>
              Next
            </Button>
          </Stack>
        }
      />

      <ReconRecoBar />

      <Stack
        direction={{ xs: "column", md: "row" }}
        justifyContent="space-between"
        alignItems={{ md: "center" }}
        gap={1.5}
        sx={{ p: 1.5, bgcolor: "var(--glass-bg)", backdropFilter: "blur(18px) saturate(150%)", border: "1px solid", borderColor: selectedCount ? "primary.main" : "divider", borderRadius: 1 }}
      >
        <Stack direction="row" spacing={1} alignItems="center" flexWrap="wrap">
          <Typography sx={{ fontSize: 13, fontWeight: 700 }}>{selectedCount} selected</Typography>
          <Button size="small" onClick={() => setSelectedIds(allVisibleSelected ? [] : sideA.map((row) => row.id))}>
            {allVisibleSelected ? "Clear view" : "Select all in view"}
          </Button>
          <Button size="small" onClick={() => setQueueSelected(true)}>
            Select all {suggestedMatch.queueSize} in queue
          </Button>
        </Stack>
        <Stack direction="row" spacing={1} flexWrap="wrap">
          <Button size="small" variant="contained" color="success" disabled={!selectedCount} onClick={() => batch("Approved")}>
            Approve all
          </Button>
          <Button size="small" variant="outlined" color="error" disabled={!selectedCount} onClick={() => batch("Rejected")}>
            Reject all
          </Button>
          <Button size="small" variant="outlined" disabled={!selectedCount} onClick={() => batch("Escalated")}>
            Escalate all
          </Button>
        </Stack>
      </Stack>

      <Box sx={{ display: "grid", gridTemplateColumns: { xs: "1fr", lg: "1fr 1.25fr 1fr" }, gap: 2.5, minHeight: 420 }}>
        <TxnList
          title="Transaction Set A"
          rows={sideA}
          selectedId={left.id}
          selectedIds={selectedIds}
          onToggle={toggleSelect}
          onSelect={(id) => {
            setIndex(sideA.findIndex((row) => row.id === id));
            const row = sideA.find((item) => item.id === id);
            if (row) setDrawerRow(row);
          }}
        />

        <Box sx={{ p: 2, bgcolor: "var(--glass-bg)", backdropFilter: "blur(18px) saturate(150%)", border: "1px solid", borderColor: "divider", borderRadius: 1 }}>
          <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ mb: 1.5 }} flexWrap="wrap" gap={1}>
            <Typography variant="h6">Suggested match</Typography>
            <StatusPill label={`SLA: ${suggestedMatch.slaRemaining}`} tone="warn" />
          </Stack>

          <Stack direction="row" alignItems="baseline" spacing={1.5} sx={{ mb: 1.5 }}>
            <Typography sx={{ fontFamily: '"IBM Plex Sans", sans-serif', fontSize: 32, fontWeight: 800, lineHeight: 1 }}>
              {suggestedMatch.confidence}
            </Typography>
            <Box
              sx={{
                px: 1.25,
                py: 0.5,
                borderRadius: 1,
                bgcolor: "primary.main",
                color: "primary.contrastText",
                fontSize: 16,
                fontWeight: 800,
              }}
            >
              {suggestedMatch.type}
            </Box>
          </Stack>
          <Stack direction="row" spacing={0.5} sx={{ mb: 2 }}>
            {matchTypes.map((type) => (
              <Box
                key={type}
                sx={{
                  px: 1,
                  py: 0.35,
                  borderRadius: 10,
                  fontSize: 10,
                  fontWeight: 800,
                  border: "1px solid",
                  borderColor: type === suggestedMatch.type ? "primary.main" : "divider",
                  color: type === suggestedMatch.type ? "primary.main" : "text.secondary",
                }}
              >
                {type}
              </Box>
            ))}
          </Stack>

          <Box sx={{ display: "grid", gridTemplateColumns: "repeat(2, 1fr)", gap: 1.25, mb: 2 }}>
            <Metric label="Amount impact" value={suggestedMatch.amountImpact} emphasis />
            <Box sx={{ p: 1.25, border: "1px solid", borderColor: "divider", borderRadius: 1 }}>
              <Typography sx={{ fontSize: 10, color: "text.secondary", textTransform: "uppercase" }}>Materiality</Typography>
              <Box sx={{ mt: 0.5 }}>
                <StatusPill label={suggestedMatch.materiality} tone={materialityTone[suggestedMatch.materiality]} />
              </Box>
            </Box>
            <Metric label="Risk" value={suggestedMatch.risk} />
            <Metric label="Queue remaining" value={String(suggestedMatch.queueSize)} />
          </Box>

          <Typography sx={{ fontSize: 12, fontWeight: 700, mb: 0.75 }}>Confidence breakdown</Typography>
          <Stack spacing={0.75} sx={{ mb: 2 }}>
            {suggestedMatch.confidenceBreakdown.map((item) => (
              <Stack key={item.label} spacing={0.3}>
                <Stack direction="row" justifyContent="space-between">
                  <Typography sx={{ fontSize: 11 }}>{item.label}</Typography>
                  <Typography sx={{ fontSize: 11, fontWeight: 700 }}>{item.weight}%</Typography>
                </Stack>
                <LinearProgress variant="determinate" value={item.weight} sx={{ height: 6, borderRadius: 99 }} />
              </Stack>
            ))}
          </Stack>

          <Typography sx={{ fontSize: 12, color: "text.secondary", mb: 1.5 }}>
            {suggestedMatch.rule} · {suggestedMatch.ruleVersion}
          </Typography>
          <Typography sx={{ fontSize: 12, fontWeight: 700, mb: 0.75 }}>Why matched</Typography>
          <Stack spacing={0.5} sx={{ mb: 1.5 }}>
            {suggestedMatch.why.map((item) => (
              <Typography key={item} sx={{ fontSize: 12 }}>
                • {item}
              </Typography>
            ))}
          </Stack>
          <Typography sx={{ fontSize: 12, fontWeight: 700, mb: 0.5 }}>Similar match analytics</Typography>
          <Stack direction="row" spacing={1} sx={{ mb: 1.25 }}>
            {suggestedMatch.similarAnalytics.map((item) => (
              <Box key={item.label} sx={{ flex: 1, p: 1, border: "1px solid", borderColor: "divider", borderRadius: 1 }}>
                <Typography sx={{ fontSize: 10, color: "text.secondary" }}>{item.label}</Typography>
                <Typography sx={{ fontFamily: '"IBM Plex Sans", sans-serif', fontWeight: 800 }}>{item.value}</Typography>
              </Box>
            ))}
          </Stack>
          <Typography sx={{ fontSize: 12, fontWeight: 700, mb: 0.5 }}>Approval rate (7 day)</Typography>
          <Stack direction="row" alignItems="flex-end" spacing={0.4} sx={{ height: 36, mb: 1.5 }}>
            {suggestedMatch.approvalRateTrend.map((value, idx) => (
              <Box
                key={`apr-${idx}`}
                sx={{
                  width: 14,
                  height: `${value - 70}%`,
                  bgcolor: idx === suggestedMatch.approvalRateTrend.length - 1 ? "success.main" : "divider",
                  borderRadius: 0.5,
                }}
              />
            ))}
          </Stack>
          <Typography sx={{ fontSize: 12, fontWeight: 700, mb: 0.5 }}>Match history</Typography>
          <Stack spacing={0.4} sx={{ mb: 1.25 }}>
            {suggestedMatch.history.map((item) => (
              <Typography key={item} sx={{ fontSize: 12, color: "text.secondary" }}>
                • {item}
              </Typography>
            ))}
          </Stack>
          <Typography sx={{ fontSize: 12, fontWeight: 700, mb: 0.5 }}>Similar matches</Typography>
          <Stack spacing={0.4} sx={{ mb: 1.25 }}>
            {suggestedMatch.similarCases.map((item) => (
              <Typography key={item} sx={{ fontSize: 12 }}>
                • {item}
              </Typography>
            ))}
          </Stack>
          <Typography sx={{ fontSize: 12, fontWeight: 700, mb: 0.5 }}>Reviewer comments</Typography>
          {suggestedMatch.comments.map((item) => (
            <Typography key={item} sx={{ fontSize: 12, mb: 1.5, color: "text.secondary" }}>
              {item}
            </Typography>
          ))}
          <Stack direction="row" useFlexGap flexWrap="wrap" spacing={1.25} sx={{ mt: 0.5 }}>
            <Button
              variant="contained"
              color="success"
              onClick={() => {
                setToast(`Approved ${left.id}`);
                goNext();
              }}
            >
              Approve
            </Button>
            <Button variant="outlined" color="error" onClick={() => setToast(`Rejected ${left.id}`)}>
              Reject
            </Button>
            <Button variant="outlined" onClick={() => navigate("/reconciliation/approvals")}>
              Escalate
            </Button>
            <Button variant="contained" color="warning" onClick={() => navigate("/exceptions/cases")}>
              Convert to exception case
            </Button>
            <Button variant="text" onClick={() => navigate("/reconciliation/manual-match")}>
              Manual match
            </Button>
          </Stack>
        </Box>

        <TxnList title="Transaction Set B" rows={sideB} selectedId={sideB[0]?.id} ranked />
      </Box>
      <ActivityTimeline />

      <Drawer anchor="right" open={Boolean(drawerRow)} onClose={() => setDrawerRow(null)}>
        <Box sx={{ width: { xs: 320, sm: 420 }, p: 2.5 }}>
          <Typography variant="h6" sx={{ mb: 0.5 }}>
            Transaction details
          </Typography>
          <Typography sx={{ fontSize: 13, color: "text.secondary", mb: 2 }}>{drawerRow?.invoice}</Typography>
          <Detail label="Invoice" value={drawerRow?.invoice} />
          <Detail label="Reference" value={drawerRow?.reference} />
          <Detail label="Currency" value={drawerRow?.currency} />
          <Detail label="Amount" value={drawerRow ? drawerRow.amount.toLocaleString() : ""} />
          <Detail label="Entity" value={drawerRow?.entity} />
          <Detail label="Counterparty" value={drawerRow?.counterparty} />
          <Detail label="Business unit" value={drawerRow?.businessUnit} />
          <Detail label="Description" value={drawerRow?.description} />
          <Detail label="SLA" value={drawerRow?.slaRemaining} />
          <Detail label="Attachments" value={drawerRow?.attachments.join(", ") || "None"} />
          <Typography sx={{ fontSize: 12, fontWeight: 700, mt: 2, mb: 0.75 }}>Historical activity</Typography>
          {suggestedMatch.history.map((item) => (
            <Typography key={item} sx={{ fontSize: 12, mt: 0.5 }}>
              {item}
            </Typography>
          ))}
          <Button sx={{ mt: 2 }} variant="outlined" onClick={() => navigate("/exceptions/cases")}>
            Convert to exception case
          </Button>
        </Box>
      </Drawer>
      <Snackbar open={Boolean(toast)} autoHideDuration={2200} onClose={() => setToast("")} message={toast} />
    </>
  );
}

function Metric({ label, value, emphasis }: { label: string; value: string; emphasis?: boolean }) {
  return (
    <Box sx={{ p: 1.25, border: "1px solid", borderColor: "divider", borderRadius: 1 }}>
      <Typography sx={{ fontSize: 10, color: "text.secondary", textTransform: "uppercase" }}>{label}</Typography>
      <Typography sx={{ fontFamily: '"IBM Plex Sans", sans-serif', fontSize: 18, fontWeight: 800, color: emphasis ? "primary.main" : "text.primary" }}>
        {value}
      </Typography>
    </Box>
  );
}

function Detail({ label, value }: { label: string; value?: string }) {
  return (
    <Stack direction="row" justifyContent="space-between" gap={2} sx={{ py: 0.75, borderBottom: "1px solid", borderColor: "divider" }}>
      <Typography sx={{ fontSize: 12, color: "text.secondary" }}>{label}</Typography>
      <Typography sx={{ fontSize: 12, fontWeight: 700, textAlign: "right" }}>{value}</Typography>
    </Stack>
  );
}

function TxnList({
  title,
  rows,
  selectedId,
  selectedIds,
  ranked,
  onSelect,
  onToggle,
}: {
  title: string;
  rows: Array<{
    id: string;
    invoice: string;
    amount: number;
    date: string;
    entity: string;
    status?: string;
    score?: number;
    slaRemaining?: string;
  }>;
  selectedId?: string;
  selectedIds?: string[];
  ranked?: boolean;
  onSelect?: (id: string) => void;
  onToggle?: (id: string) => void;
}) {
  return (
    <Box sx={{ bgcolor: "var(--glass-bg)", backdropFilter: "blur(18px) saturate(150%)", border: "1px solid", borderColor: "divider", borderRadius: 1, overflow: "auto", maxHeight: 760 }}>
      <Typography variant="h6" sx={{ p: 1.5, pb: 1 }}>
        {title}
      </Typography>
      {rows.map((row) => {
        const selected = row.id === selectedId;
        const checked = selectedIds?.includes(row.id);
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
              cursor: onSelect || ranked ? "pointer" : "default",
              borderTop: "1px solid",
              borderColor: "divider",
              bgcolor: selected ? "var(--indigo-soft)" : "transparent",
            }}
          >
            <Stack direction="row" justifyContent="space-between" alignItems="flex-start" gap={1}>
              <Stack direction="row" spacing={0.75} alignItems="flex-start">
                {onToggle && (
                  <Checkbox
                    size="small"
                    checked={Boolean(checked)}
                    onClick={(event) => event.stopPropagation()}
                    onChange={() => onToggle(row.id)}
                    sx={{ p: 0, mt: 0.2 }}
                  />
                )}
                <Box>
                  <Typography sx={{ fontWeight: 700, fontSize: 12 }}>{row.invoice}</Typography>
                  <Typography sx={{ fontSize: 11, color: "text.secondary" }}>
                    {row.entity} · {row.date}
                    {row.status ? ` · ${row.status}` : ""}
                    {row.slaRemaining ? ` · SLA ${row.slaRemaining}` : ""}
                  </Typography>
                </Box>
              </Stack>
              <Typography sx={{ fontFamily: '"IBM Plex Sans", sans-serif', fontSize: 12, fontWeight: 700 }}>
                {row.amount.toLocaleString()}
              </Typography>
            </Stack>
            {ranked && row.score != null && (
              <Stack spacing={0.4} sx={{ mt: 0.75 }}>
                <Stack direction="row" justifyContent="space-between">
                  <Typography sx={{ fontSize: 10, color: "text.secondary" }}>Candidate score</Typography>
                  <Typography sx={{ fontSize: 11, fontWeight: 800, fontFamily: '"IBM Plex Sans", sans-serif' }}>{row.score}</Typography>
                </Stack>
                <LinearProgress variant="determinate" value={row.score} sx={{ height: 6, borderRadius: 99 }} />
              </Stack>
            )}
          </Box>
        );
      })}
    </Box>
  );
}
