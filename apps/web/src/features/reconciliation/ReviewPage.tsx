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
import { sideA, sideB, suggestedMatch } from "./data";

const matchTypes = ["1:1", "1:M", "M:1", "M:M"] as const;

type SideARow = (typeof sideA)[number];

export function ReviewPage() {
  const [params] = useSearchParams();
  const navigate = useNavigate();
  const [index, setIndex] = useState(0);
  const [selectedIds, setSelectedIds] = useState<string[]>([]);
  const [drawerRow, setDrawerRow] = useState<SideARow | null>(null);
  const [toast, setToast] = useState("");
  const left = sideA[index] ?? sideA[0];
  const runId = params.get("run") ?? "IC-2026-08-17";

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
    setSelectedIds((current) => (current.includes(id) ? current.filter((item) => item !== id) : [...current, id]));
  };

  const batch = (action: string) => {
    if (!selectedIds.length) return;
    setToast(`${action} ${selectedIds.length} matches`);
    setSelectedIds([]);
  };

  return (
    <>
      <PageHeader
        title="Review Workbench"
        description={`Run ${runId}. Shortcuts: A approve · R reject · E escalate · N next.`}
        actions={
          <Stack direction="row" spacing={1}>
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

      {selectedIds.length > 0 && (
        <Stack
          direction={{ xs: "column", md: "row" }}
          justifyContent="space-between"
          alignItems={{ md: "center" }}
          gap={1.5}
          sx={{ p: 1.5, bgcolor: "background.paper", border: "1px solid", borderColor: "primary.main", borderRadius: 1 }}
        >
          <Typography sx={{ fontSize: 13, fontWeight: 700 }}>{selectedIds.length} matches selected</Typography>
          <Stack direction="row" spacing={1} flexWrap="wrap">
            <Button size="small" variant="contained" color="success" onClick={() => batch("Approved")}>
              Approve group
            </Button>
            <Button size="small" variant="outlined" color="error" onClick={() => batch("Rejected")}>
              Reject group
            </Button>
            <Button size="small" variant="outlined" onClick={() => batch("Escalated")}>
              Escalate group
            </Button>
          </Stack>
        </Stack>
      )}

      <Box sx={{ display: "grid", gridTemplateColumns: { xs: "1fr", lg: "1fr 1.25fr 1fr" }, gap: 2.5, minHeight: 420 }}>
        <TxnList
          title="Transaction Set A"
          rows={sideA}
          selectedId={left.id}
          selectedIds={selectedIds}
          onToggle={toggleSelect}
          onSelect={(id) => setIndex(sideA.findIndex((row) => row.id === id))}
          onOpen={(row) => setDrawerRow(row)}
        />

        <Box sx={{ p: 2, bgcolor: "background.paper", border: "1px solid", borderColor: "divider", borderRadius: 1 }}>
          <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ mb: 1.25 }}>
            <Typography variant="h6">Suggested match</Typography>
            <Stack direction="row" spacing={0.5}>
              {matchTypes.map((type) => (
                <Box
                  key={type}
                  sx={{
                    px: 1,
                    py: 0.4,
                    borderRadius: 10,
                    fontSize: 11,
                    fontWeight: 800,
                    border: "1px solid",
                    borderColor: type === suggestedMatch.type ? "primary.main" : "divider",
                    bgcolor: type === suggestedMatch.type ? "var(--indigo-soft)" : "transparent",
                    color: type === suggestedMatch.type ? "primary.main" : "text.secondary",
                  }}
                >
                  {type}
                </Box>
              ))}
            </Stack>
          </Stack>

          <Box sx={{ display: "grid", gridTemplateColumns: "repeat(2, 1fr)", gap: 1.25, mb: 2 }}>
            <Metric label="Confidence" value={suggestedMatch.confidence} />
            <Metric label="Amount impact" value={suggestedMatch.amountImpact} emphasis />
            <Metric label="Materiality" value={suggestedMatch.materiality} />
            <Metric label="Risk" value={suggestedMatch.risk} />
          </Box>

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
          <Typography sx={{ fontSize: 12, color: "text.secondary", mb: 2 }}>{suggestedMatch.historical}</Typography>
          <Stack direction="row" spacing={1} flexWrap="wrap">
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
            <Button variant="text" onClick={() => navigate("/reconciliation/manual-match")}>
              Manual match
            </Button>
            <Button size="small" onClick={() => setDrawerRow(left)}>
              Audit trail
            </Button>
          </Stack>
        </Box>

        <TxnList title="Transaction Set B" rows={sideB} selectedId={sideB[0]?.id} ranked />
      </Box>
      <ActivityTimeline />

      <Drawer anchor="right" open={Boolean(drawerRow)} onClose={() => setDrawerRow(null)}>
        <Box sx={{ width: { xs: 320, sm: 400 }, p: 2.5 }}>
          <Typography variant="h6" sx={{ mb: 2 }}>
            {drawerRow?.invoice}
          </Typography>
          <Detail label="Reference" value={drawerRow?.reference} />
          <Detail label="Invoice" value={drawerRow?.invoice} />
          <Detail label="Currency" value={drawerRow?.currency} />
          <Detail label="Amount" value={drawerRow ? drawerRow.amount.toLocaleString() : ""} />
          <Detail label="Counterparty" value={drawerRow?.counterparty} />
          <Detail label="Business unit" value={drawerRow?.businessUnit} />
          <Detail label="Entity" value={drawerRow?.entity} />
          <Detail label="Date" value={drawerRow?.date} />
          <Detail label="Attachments" value={drawerRow?.attachments.join(", ") || "None"} />
          <Typography sx={{ fontSize: 12, fontWeight: 700, mt: 2, mb: 0.75 }}>Audit trail</Typography>
          <Typography sx={{ fontSize: 12, color: "text.secondary" }}>Rule {suggestedMatch.ruleVersion}</Typography>
          {suggestedMatch.history.map((item) => (
            <Typography key={item} sx={{ fontSize: 12, mt: 0.5 }}>
              {item}
            </Typography>
          ))}
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
    <Stack direction="row" justifyContent="space-between" sx={{ py: 0.75, borderBottom: "1px solid", borderColor: "divider" }}>
      <Typography sx={{ fontSize: 12, color: "text.secondary" }}>{label}</Typography>
      <Typography sx={{ fontSize: 12, fontWeight: 700 }}>{value}</Typography>
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
  onOpen,
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
    reference?: string;
    currency?: string;
    counterparty?: string;
    businessUnit?: string;
    attachments?: string[];
  }>;
  selectedId?: string;
  selectedIds?: string[];
  ranked?: boolean;
  onSelect?: (id: string) => void;
  onToggle?: (id: string) => void;
  onOpen?: (row: SideARow) => void;
}) {
  return (
    <Box sx={{ bgcolor: "background.paper", border: "1px solid", borderColor: "divider", borderRadius: 1, overflow: "auto" }}>
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
            {onOpen && (
              <Button
                size="small"
                sx={{ mt: 0.5, px: 0 }}
                onClick={(event) => {
                  event.stopPropagation();
                  onOpen(row as SideARow);
                }}
              >
                Details
              </Button>
            )}
          </Box>
        );
      })}
    </Box>
  );
}
