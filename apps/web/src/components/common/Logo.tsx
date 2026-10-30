import { Box, Stack, Typography } from "@mui/material";

/** ufme mark: the serif initials on navy, with the green "matched" square. */
export function LogoMark({ size = 26 }: { size?: number }) {
  return (
    <Box component="svg" viewBox="0 0 32 32" sx={{ width: size, height: size, display: "block", flexShrink: 0 }} aria-hidden>
      <rect width="32" height="32" rx="4" fill="var(--text-primary)" />
      <text x="5" y="22" fontFamily="var(--font-display)" fontSize="17" fill="var(--bg-surface)">uf</text>
      <rect x="24" y="17" width="4" height="4" fill="var(--brand-lime)" />
    </Box>
  );
}

/** Wordmark: lowercase serif "ufme" closed by a green square (the matched item). */
export function Logo() {
  return (
    <Stack direction="row" alignItems="baseline" spacing={0.4} sx={{ color: "text.primary", userSelect: "none" }}>
      <Typography component="span" sx={{ fontFamily: "var(--font-display)", fontSize: 30, fontWeight: 500, letterSpacing: "-0.03em", lineHeight: 1 }}>
        ufme
      </Typography>
      <Box component="span" aria-hidden sx={{ width: 7, height: 7, bgcolor: "var(--brand-indigo)", display: "inline-block" }} />
    </Stack>
  );
}
