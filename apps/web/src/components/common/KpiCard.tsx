import { Box, Stack, Typography } from "@mui/material";

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
  valueColor = "#0f172a",
}: KpiCardProps) {
  return (
    <Box
      className="card-enter"
      sx={{
        bgcolor: "#fff",
        border: "1px solid #e2e8f0",
        borderRadius: 1,
        p: 1.75,
        position: "relative",
        overflow: "hidden",
        boxShadow: "0 1px 2px rgba(0,0,0,0.05)",
        transition: "transform 0.2s ease, box-shadow 0.2s ease",
        "&:hover": {
          transform: "translateY(-2px)",
          boxShadow: "0 4px 6px -1px rgba(0,0,0,0.07)",
          "&::before": { opacity: 1 },
        },
        "&::before": {
          content: '""',
          position: "absolute",
          top: 0,
          left: 0,
          right: 0,
          height: "3px",
          bgcolor: "#4f46e5",
          opacity: 0,
          transition: "opacity 0.2s ease",
        },
      }}
    >
      <Typography
        sx={{
          fontSize: 11,
          fontWeight: 600,
          letterSpacing: "0.05em",
          textTransform: "uppercase",
          color: "#94a3b8",
        }}
      >
        {label}
      </Typography>
      <Stack direction="row" alignItems="baseline" spacing={0.75} sx={{ my: 0.75 }}>
        <Typography
          className="mono"
          sx={{ fontFamily: '"IBM Plex Sans", sans-serif', fontSize: 24, fontWeight: 700, color: valueColor }}
        >
          {value}
        </Typography>
        {change ? (
          <Box
            sx={{
              fontSize: 11,
              fontWeight: 600,
              px: 0.6,
              py: 0.15,
              borderRadius: 0.5,
              bgcolor: changeDir === "down" ? "#fef2f2" : "#ecfdf5",
              color: changeDir === "down" ? "#dc2626" : "#059669",
            }}
          >
            {change}
          </Box>
        ) : null}
      </Stack>
      <Stack direction="row" justifyContent="space-between">
        <Typography sx={{ fontSize: 11, color: footerLeft.includes("Critical") ? "#dc2626" : "#475569" }}>
          {footerLeft}
        </Typography>
        {footerRight ? (
          <Typography sx={{ fontSize: 11, fontWeight: 600, color: footerRight === "MED RISK" ? "#d97706" : "#4f46e5" }}>
            {footerRight}
          </Typography>
        ) : null}
      </Stack>
    </Box>
  );
}
