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
        bgcolor: "background.paper",
        border: "1px solid",
        borderColor: "divider",
        borderRadius: 1,
        p: 2.25,
      }}
    >
      <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ mb: 1.75 }}>
        <Typography variant="h6">{title}</Typography>
        {action}
      </Stack>
      {children}
    </Box>
  );
}

export function StatusPill({ label, tone }: { label: string; tone: "ok" | "warn" | "crit" }) {
  const styles = {
    ok: { bgcolor: "var(--emerald-soft)", color: "var(--brand-emerald)", border: "1px solid rgba(5,150,105,0.3)" },
    warn: { bgcolor: "var(--amber-soft)", color: "var(--brand-amber)", border: "1px solid rgba(217,119,6,0.3)" },
    crit: { bgcolor: "var(--crimson-soft)", color: "var(--brand-crimson)", border: "1px solid rgba(220,38,38,0.3)" },
  };
  return (
    <Box sx={{ display: "inline-block", fontSize: 10, fontWeight: 700, px: 1, py: 0.35, borderRadius: 10, ...styles[tone] }}>
      {label}
    </Box>
  );
}
