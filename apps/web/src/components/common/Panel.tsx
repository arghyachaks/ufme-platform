import type { ReactNode } from "react";
import { Box, Stack, Typography } from "@mui/material";

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
      className="card-enter"
      sx={{
        bgcolor: "var(--bg-surface)",
        border: "1px solid var(--glass-border)",
        borderRadius: "2px",
        minWidth: 0,
      }}
    >
      <Stack
        direction="row"
        justifyContent="space-between"
        alignItems="center"
        gap={2}
        sx={{ px: 3, py: 2, borderBottom: "1px solid var(--glass-border)", flexWrap: "wrap" }}
      >
        <Typography variant="h6" component="h2" sx={{ fontSize: 24 }}>{title}</Typography>
        {action}
      </Stack>
      <Box sx={{ minWidth: 0, overflowX: "auto", p: 3 }}>{children}</Box>
    </Box>
  );
}

export function StatusPill({ label, tone }: { label: string; tone: "ok" | "warn" | "crit" }) {
  const styles = {
    ok: { bgcolor: "var(--emerald-soft)", color: "var(--text-primary)" },
    warn: { bgcolor: "var(--amber-soft)", color: "var(--text-primary)" },
    crit: { bgcolor: "var(--crimson-soft)", color: "var(--text-primary)" },
  };
  return (
    <Box
      component="span"
      sx={{ display: "inline-block", fontSize: 12, fontWeight: 500, px: 1.1, py: 0.35, borderRadius: "9999px", whiteSpace: "nowrap", lineHeight: 1.3, ...styles[tone] }}
    >
      {label}
    </Box>
  );
}
