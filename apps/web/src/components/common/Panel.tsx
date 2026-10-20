import type { ReactNode } from "react";
import { Box, Stack, Typography } from "@mui/material";
import { spotlight } from "./Motion";

export function Panel({
  title,
  action,
  children,
}: {
  title: string;
  action?: ReactNode;
  children: ReactNode;
}) {
  return (
    <Box
      className="card-enter spotlight"
      onMouseMove={spotlight}
      sx={{
        bgcolor: "var(--bg-surface)",
        border: "1px solid",
        borderColor: "var(--glass-border)",
        borderRadius: "10px",
        p: 2.5,
        transition: "box-shadow 0.55s cubic-bezier(0.22, 1, 0.36, 1), border-color 0.5s cubic-bezier(0.22, 1, 0.36, 1), transform 0.55s cubic-bezier(0.22, 1, 0.36, 1)",
      }}
    >
      <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ mb: 2, mx: -2.5, mt: -0.5, px: 2.5, pb: 1.5, borderBottom: "1px solid var(--border-subtle)" }}>
        <Typography variant="h6">{title}</Typography>
        {action}
      </Stack>
      <Box sx={{ minWidth: 0, overflowX: "auto" }}>{children}</Box>
    </Box>
  );
}

export function StatusPill({ label, tone }: { label: string; tone: "ok" | "warn" | "crit" }) {
  const styles = {
    ok: { bgcolor: "var(--emerald-soft)", color: "var(--brand-emerald)", border: "1px solid color-mix(in srgb, var(--brand-emerald) 28%, transparent)" },
    warn: { bgcolor: "var(--amber-soft)", color: "var(--brand-amber)", border: "1px solid color-mix(in srgb, var(--brand-amber) 28%, transparent)" },
    crit: { bgcolor: "var(--crimson-soft)", color: "var(--brand-crimson)", border: "1px solid color-mix(in srgb, var(--brand-crimson) 28%, transparent)" },
  };
  return (
    <Box sx={{ display: "inline-block", fontSize: 10.5, fontWeight: 500, fontFamily: "var(--font-mono)", letterSpacing: "0.03em", px: 0.9, py: 0.25, borderRadius: "5px", ...styles[tone] }}>
      {label}
    </Box>
  );
}
