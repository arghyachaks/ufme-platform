import { Box } from "@mui/material";
import { workspaceApi, type DashboardData } from "../../api/services";
import { useQuery } from "../../api/useQuery";

export function ActivityTicker() {
  const { data } = useQuery(workspaceApi.dashboard);
  return data ? <ActivityTickerView d={data} /> : null;
}

function ActivityTickerView({ d }: { d: DashboardData }) {
  const { tickerItems } = d;
  return (
    <Box
      className="ufme-footer"
      sx={{
        bgcolor: "transparent",
        color: "var(--text-secondary)",
        fontFamily: "var(--font-mono)",
        display: "flex",
        alignItems: "center",
        overflow: "hidden",
        px: 2,
        fontSize: 11,
      }}
    >
      <Box className="ticker-track">
        {tickerItems.map((item) => (
          <span key={item}>{item}</span>
        ))}
      </Box>
    </Box>
  );
}
