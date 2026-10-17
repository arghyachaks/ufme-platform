import { Box, Stack, Typography } from "@mui/material";
import { workspaceApi, type ReconData } from "../../api/services";
import { useQuery } from "../../api/useQuery";

export function ActivityTimeline() {
  const { data } = useQuery(workspaceApi.recon);
  return data ? <ActivityTimelineView d={data} /> : null;
}

function ActivityTimelineView({ d }: { d: ReconData }) {
  const { reconActivity } = d;
  return (
    <Box className="glass" sx={{ p: 1.5, borderRadius: 2 }}>
      <Typography variant="h6" sx={{ mb: 1 }}>
        Activity timeline
      </Typography>
      <Stack spacing={0.75}>
        {reconActivity.map((item) => (
          <Stack key={`${item.time}-${item.text}`} direction="row" spacing={1}>
            <Typography sx={{ fontFamily: '"IBM Plex Sans", sans-serif', fontSize: 11, color: "text.secondary", minWidth: 40 }}>
              {item.time}
            </Typography>
            <Typography sx={{ fontSize: 11, fontWeight: 700, minWidth: 36 }}>{item.actor}</Typography>
            <Typography sx={{ fontSize: 12 }}>{item.text}</Typography>
          </Stack>
        ))}
      </Stack>
    </Box>
  );
}
