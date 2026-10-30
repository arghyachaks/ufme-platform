import type { ReactNode } from "react";
import { useState } from "react";
import {
  Box, Checkbox, LinearProgress, Skeleton, Snackbar, Stack, Table, TableBody, TableCell, TableHead, TableRow, Typography,
} from "@mui/material";
import type { Kpi, Severity, Tone } from "../../api/types";
import { PageHeader } from "./PageHeader";

export const mono = { fontFamily: 'var(--font-mono)' } as const;
export const glass = {
  bgcolor: "var(--glass-bg)",
    border: "1px solid",
  borderColor: "var(--glass-border)",
  borderRadius: "2px",
} as const;

export const severityTone: Record<Severity, Tone> = { Critical: "crit", High: "crit", Medium: "warn", Low: "ok" };

export function money(value: number, currency = "USD") {
  const abs = Math.abs(value);
  const short = abs >= 1e6 ? `${(value / 1e6).toFixed(2)}M` : abs >= 1e3 ? `${(value / 1e3).toFixed(1)}K` : value.toFixed(0);
  return `${short} ${currency}`;
}

/** Standard page frame: header + vertical rhythm + loading state. */
export function Page({ title, description, actions, loading, children }: {
  title: string; description: string; actions?: ReactNode; loading?: boolean; children?: ReactNode;
}) {
  return (
    <Stack spacing={2.5}>
      <PageHeader title={title} description={description} actions={actions} />
      {loading ? (
        <Stack spacing={2}>
          <Skeleton variant="rounded" height={72} />
          <Skeleton variant="rounded" height={320} />
        </Stack>
      ) : (
        children
      )}
    </Stack>
  );
}

/** Flat pastel fills (the editorial system's cards): status tones keep their meaning, neutral cards rotate. */
const toneFill: Record<Tone, string> = { ok: "var(--emerald-soft)", warn: "var(--amber-soft)", crit: "var(--crimson-soft)" };
const neutralFills = ["var(--blue-soft)", "var(--lavender-soft)", "var(--bg-muted)", "var(--indigo-soft)"];

export function StatGrid({ items }: { items: Kpi[] }) {
  return (
    <Box sx={{ display: "grid", gridTemplateColumns: { xs: "1fr", sm: "1fr 1fr", lg: `repeat(${Math.min(items.length, 5)}, minmax(0, 1fr))` }, gap: 2 }}>
      {items.map((kpi, i) => (
        <Box
          key={kpi.label}
          className="card-enter"
          sx={{ p: 3, borderRadius: "2px", bgcolor: kpi.tone ? toneFill[kpi.tone] : neutralFills[i % neutralFills.length], display: "flex", flexDirection: "column", gap: 1, minWidth: 0 }}
        >
          <Typography sx={{ fontSize: 14, color: "text.primary" }}>{kpi.label}</Typography>
          <Typography
            className="display"
            sx={{ fontSize: "clamp(30px, 3vw, 46px)", lineHeight: 1, color: "text.primary", whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}
          >
            {kpi.value}
          </Typography>
          {kpi.hint ? <Typography sx={{ ...mono, fontSize: 12.5, color: "text.secondary" }}>{kpi.hint}</Typography> : null}
        </Box>
      ))}
    </Box>
  );
}

export type Column<T> = { key: string; header: string; render: (row: T) => ReactNode; width?: number | string; align?: "right" | "left" | "center" };

export function DataTable<T>({ rows, columns, rowKey, onRowClick, selectedKey, selectable, checked, onCheckedChange, empty = "Nothing to show." }: {
  rows: T[];
  columns: Column<T>[];
  rowKey: (row: T) => string;
  onRowClick?: (row: T) => void;
  selectedKey?: string;
  selectable?: boolean;
  checked?: string[];
  onCheckedChange?: (keys: string[]) => void;
  empty?: string;
}) {
  const keys = rows.map(rowKey);
  const sel = checked ?? [];
  const all = rows.length > 0 && sel.length === rows.length;
  return (
    <Box sx={{ ...glass, overflowX: "auto" }}>
      <Table size="small">
        <TableHead>
          <TableRow>
            {selectable ? (
              <TableCell padding="checkbox">
                <Checkbox size="small" checked={all} indeterminate={sel.length > 0 && !all} onChange={() => onCheckedChange?.(all ? [] : keys)} />
              </TableCell>
            ) : null}
            {columns.map((c) => (
              <TableCell key={c.key} align={c.align} sx={{ width: c.width, whiteSpace: "nowrap" }}>{c.header}</TableCell>
            ))}
          </TableRow>
        </TableHead>
        <TableBody>
          {rows.length === 0 ? (
            <TableRow>
              <TableCell colSpan={columns.length + (selectable ? 1 : 0)} sx={{ textAlign: "center", color: "text.secondary", py: 4 }}>{empty}</TableCell>
            </TableRow>
          ) : (
            rows.map((row) => {
              const key = rowKey(row);
              return (
                <TableRow key={key} hover selected={selectedKey === key} onClick={() => onRowClick?.(row)} sx={{ cursor: onRowClick ? "pointer" : "default" }}>
                  {selectable ? (
                    <TableCell padding="checkbox" onClick={(e) => e.stopPropagation()}>
                      <Checkbox size="small" checked={sel.includes(key)}
                        onChange={() => onCheckedChange?.(sel.includes(key) ? sel.filter((k) => k !== key) : [...sel, key])} />
                    </TableCell>
                  ) : null}
                  {columns.map((c) => <TableCell key={c.key} align={c.align}>{c.render(row)}</TableCell>)}
                </TableRow>
              );
            })
          )}
        </TableBody>
      </Table>
    </Box>
  );
}

export function Meter({ value, max = 100, tone, label }: { value: number; max?: number; tone?: Tone; label?: string }) {
  const pct = Math.max(0, Math.min(100, (value / max) * 100));
  const auto: Tone = tone ?? (pct >= 90 ? "crit" : pct >= 75 ? "warn" : "ok");
  return (
    <Stack spacing={0.5} sx={{ minWidth: 90 }}>
      {label ? <Typography sx={{ fontSize: 11, color: "text.secondary" }}>{label}</Typography> : null}
      <LinearProgress variant="determinate" value={pct} color={auto === "crit" ? "error" : auto === "warn" ? "warning" : "success"} sx={{ height: 6, borderRadius: 3 }} />
    </Stack>
  );
}

export function Sparkline({ values, width = 240, height = 56, color = "var(--brand-indigo)" }: { values: number[]; width?: number; height?: number; color?: string }) {
  const min = Math.min(...values);
  const max = Math.max(...values);
  const span = max - min || 1;
  const pts = values.map((v, i) => `${(i / (values.length - 1)) * width},${height - 4 - ((v - min) / span) * (height - 8)}`).join(" ");
  return (
    <svg width="100%" viewBox={`0 0 ${width} ${height}`} preserveAspectRatio="none" style={{ display: "block" }}>
      <polyline points={pts} fill="none" stroke={color} strokeWidth={2} strokeLinejoin="round" />
    </svg>
  );
}

export function useToast() {
  const [message, setMessage] = useState("");
  const node = (
    <Snackbar open={Boolean(message)} autoHideDuration={2600} onClose={() => setMessage("")} message={message}
      anchorOrigin={{ vertical: "bottom", horizontal: "center" }} />
  );
  return { toast: setMessage, toastNode: node };
}

export function KeyValue({ label, value }: { label: string; value: ReactNode }) {
  return (
    <Stack direction="row" justifyContent="space-between" spacing={2} sx={{ py: 0.6, borderBottom: "1px dashed", borderColor: "divider" }}>
      <Typography sx={{ fontSize: 12, color: "text.secondary" }}>{label}</Typography>
      <Typography component="div" sx={{ fontSize: 12, fontWeight: 600, textAlign: "right" }}>{value}</Typography>
    </Stack>
  );
}

export function PageSkeleton() {
  return (
    <Stack spacing={2}>
      <Skeleton variant="rounded" height={56} />
      <Skeleton variant="rounded" height={96} />
      <Skeleton variant="rounded" height={360} />
    </Stack>
  );
}
