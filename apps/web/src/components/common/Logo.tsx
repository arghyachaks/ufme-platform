import { Box, Stack, Typography } from "@mui/material";

/** UFME mark: two interlocking brackets — a debit and a credit closing on one matched point. */
export function LogoMark({ size = 26 }: { size?: number }) {
  return (
    <Box component="svg" viewBox="0 0 32 32" sx={{ width: size, height: size, display: "block", flexShrink: 0 }} aria-hidden>
      <rect width="32" height="32" rx="8" fill="var(--bg-muted)" stroke="var(--border-strong)" />
      <path d="M9 9v9a4 4 0 0 0 4 4h1" fill="none" stroke="var(--brand-indigo)" strokeWidth="2.6" strokeLinecap="round" />
      <path d="M23 23v-9a4 4 0 0 0-4-4h-1" fill="none" stroke="var(--text-primary)" strokeWidth="2.6" strokeLinecap="round" />
      <circle cx="16" cy="16" r="2" fill="var(--brand-indigo)" />
    </Box>
  );
}

export function Logo() {
  return (
    <Stack direction="row" alignItems="center" spacing={1.25}>
      <LogoMark />
      <Typography sx={{ fontWeight: 600, fontSize: 16, letterSpacing: "-0.03em", color: "text.primary" }}>
        ufme
      </Typography>
      <Box
        className="mono"
        sx={{ fontSize: 10, color: "text.secondary", border: "1px solid var(--border-strong)", borderRadius: "5px", px: 0.6, py: 0.1 }}
      >
        ENTERPRISE
      </Box>
    </Stack>
  );
}
