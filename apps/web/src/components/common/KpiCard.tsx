import { Box, Stack, Typography } from "@mui/material";
import { CountUp, spotlight } from "./Motion";

type KpiCardProps = {
  label: string;
  value: string;
  change?: string;
  changeDir?: "up" | "down";
  footerLeft: string;
  footerRight?: string;
  valueColor?: string;
};

export function KpiCard({
  label,
  value,
  change,
  changeDir,
  footerLeft,
  footerRight,
  valueColor = "var(--text-primary)",
}: KpiCardProps) {
  return (
    <Box
      className="card-enter spotlight"
      onMouseMove={spotlight}
      sx={{
        border: "1px solid var(--glass-border)",
        borderRadius: "10px",
        bgcolor: "var(--bg-surface)",
        p: 2,
        position: "relative",
        overflow: "hidden",
        transition: "transform 0.2s ease, box-shadow 0.2s ease",
        "&:hover": {
          borderColor: "var(--border-strong)",
          "&::before": { opacity: 1 },
        },
        "&::before": {
          content: '""',
          position: "absolute",
          top: 0,
          left: 0,
          right: 0,
          height: "1px",
          background: "linear-gradient(90deg, transparent, var(--brand-indigo), transparent)",
          opacity: 0,
          transition: "opacity 0.2s ease",
        },
      }}
    >
      <Typography
        sx={{
          fontFamily: "var(--font-mono)",
          fontSize: 10.5,
          fontWeight: 500,
          letterSpacing: "0.07em",
          textTransform: "uppercase",
          color: "var(--text-muted)",
        }}
      >
        {label}
      </Typography>
      <Stack direction="row" alignItems="baseline" spacing={0.75} sx={{ my: 1 }}>
        <Typography
          className="display"
          sx={{ fontSize: "clamp(20px, 1.7vw, 26px)", lineHeight: 1.1, color: valueColor, whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis", minWidth: 0 }}
        >
          <CountUp value={value} />
        </Typography>
        {change ? (
          <Box
            sx={{
              fontSize: 11,
              fontWeight: 600,
              px: 0.6,
              py: 0.15,
              borderRadius: "4px",
              fontFamily: "var(--font-mono)",
              bgcolor: changeDir === "down" ? "var(--crimson-soft)" : "var(--emerald-soft)",
              color: changeDir === "down" ? "var(--brand-crimson)" : "var(--brand-emerald)",
            }}
          >
            {change}
          </Box>
        ) : null}
      </Stack>
      <Stack direction="row" justifyContent="space-between">
        <Typography sx={{ fontSize: 11, color: footerLeft.includes("Critical") ? "var(--brand-crimson)" : "var(--text-secondary)" }}>
          {footerLeft}
        </Typography>
        {footerRight ? (
          <Typography sx={{ fontSize: 11, fontWeight: 600, color: footerRight === "MED RISK" ? "var(--brand-amber)" : "var(--brand-indigo)" }}>
            {footerRight}
          </Typography>
        ) : null}
      </Stack>
    </Box>
  );
}
