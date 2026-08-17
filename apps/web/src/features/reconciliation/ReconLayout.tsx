import { NavLink, Outlet, useLocation, useNavigate } from "react-router-dom";
import { Box, Button, MenuItem, Select, Stack, Typography } from "@mui/material";
import { aiRecoCard, reconContext } from "./data";

const steps = [
  { label: "Runs", to: "/reconciliation/runs" },
  { label: "Review", to: "/reconciliation/review" },
  { label: "Manual Match", to: "/reconciliation/manual-match" },
  { label: "Approvals", to: "/reconciliation/approvals" },
  { label: "Signoff", to: "/reconciliation/signoff" },
];

export function ReconLayout() {
  const { pathname } = useLocation();
  const navigate = useNavigate();

  return (
    <Stack spacing={3}>
      <Stack
        direction={{ xs: "column", md: "row" }}
        justifyContent="space-between"
        alignItems={{ md: "center" }}
        gap={2}
        sx={{
          p: 2,
          bgcolor: "background.paper",
          border: "1px solid",
          borderColor: "divider",
          borderRadius: 1,
        }}
      >
        <Stack direction="row" spacing={1} flexWrap="wrap">
          <Select size="small" value={reconContext.period} sx={{ minWidth: 120 }}>
            <MenuItem value={reconContext.period}>{reconContext.period}</MenuItem>
          </Select>
          <Select size="small" value={reconContext.entity} sx={{ minWidth: 110 }}>
            <MenuItem value={reconContext.entity}>{reconContext.entity}</MenuItem>
          </Select>
          <Select size="small" value={reconContext.type} sx={{ minWidth: 150 }}>
            <MenuItem value={reconContext.type}>{reconContext.type}</MenuItem>
          </Select>
        </Stack>
        <Button variant="contained" onClick={() => navigate("/reconciliation/runs")}>
          Run Reconciliation
        </Button>
      </Stack>

      <Stack direction="row" spacing={1} sx={{ overflowX: "auto", pb: 0.5 }}>
        {steps.map((step, index) => {
          const active = pathname === step.to;
          return (
            <Button
              key={step.to}
              component={NavLink}
              to={step.to}
              size="small"
              variant={active ? "contained" : "outlined"}
              sx={{ whiteSpace: "nowrap" }}
            >
              {index + 1}. {step.label}
            </Button>
          );
        })}
      </Stack>

      <Box sx={{ display: "flex", flexDirection: "column", gap: 3 }}>
        <Outlet />
      </Box>
    </Stack>
  );
}

export function ReconRecoBar() {
  const navigate = useNavigate();
  return (
    <Box
      className="card-enter"
      sx={{
        p: 2.25,
        borderRadius: 1,
        bgcolor: "background.paper",
        border: "1px solid",
        borderColor: "primary.main",
        boxShadow: "0 0 0 3px var(--indigo-soft)",
      }}
    >
      <Stack direction={{ xs: "column", md: "row" }} justifyContent="space-between" gap={2} alignItems={{ md: "center" }}>
        <Box>
          <Typography sx={{ fontSize: 11, fontWeight: 700, letterSpacing: "0.06em", textTransform: "uppercase", color: "primary.main" }}>
            AI Recommendation Card
          </Typography>
          <Typography sx={{ fontSize: 16, fontWeight: 700, mt: 0.5 }}>{aiRecoCard.title}</Typography>
          <Typography sx={{ fontSize: 12, color: "text.secondary", mt: 0.5 }}>{aiRecoCard.detail}</Typography>
          <Stack direction="row" spacing={2} sx={{ mt: 1 }}>
            <Typography sx={{ fontSize: 12 }}>
              Confidence <Box component="strong" sx={{ fontFamily: '"IBM Plex Sans", sans-serif' }}>{aiRecoCard.confidence}</Box>
            </Typography>
            <Typography sx={{ fontSize: 12, color: "success.main", fontWeight: 700 }}>{aiRecoCard.impact}</Typography>
            <Typography sx={{ fontSize: 12 }}>Execution time {aiRecoCard.executionTime}</Typography>
          </Stack>
        </Box>
        <Button variant="contained" onClick={() => navigate("/rules/simulation")}>
          One-click execute
        </Button>
      </Stack>
    </Box>
  );
}
