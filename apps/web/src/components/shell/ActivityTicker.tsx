import { Box } from "@mui/material";
import { tickerItems } from "../../features/dashboard/mockData";

export function ActivityTicker() {
  return (
    <Box
      className="ufme-footer"
      sx={{
        bgcolor: "#1e293b",
        color: "#fff",
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
