import { NavLink, Outlet, useLocation, useNavigate } from "react-router-dom";
import { Box, Button, MenuItem, Select, Stack, Typography } from "@mui/material";
import { reconContext } from "./data";

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
  return (
    <Box
      sx={{
        p: 1.25,
        borderRadius: 1,
        bgcolor: "var(--indigo-soft)",
        border: "1px solid",
        borderColor: "divider",
      }}
    >
      <Typography sx={{ fontSize: 11, fontWeight: 700, color: "primary.main", mb: 0.5 }}>
        Recommended next action
      </Typography>
      <Typography sx={{ fontSize: 12 }}>Apply SG- prefix strip · Confidence 98.4% · Impact +$210M auto-match</Typography>
    </Box>
  );
}
