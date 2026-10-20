import { Link as RouterLink, useParams } from "react-router-dom";
import { Box, Button, LinearProgress, Stack, Typography } from "@mui/material";
import { Panel } from "../../components/common/Panel";
import { PageHeader } from "../../components/common/PageHeader";
import { workspaceApi, type DashboardData } from "../../api/services";
import { useQuery } from "../../api/useQuery";
import { PageSkeleton } from "../../components/common/Blocks";

export function EntityRiskPage() {
  const { data } = useQuery(workspaceApi.dashboard);
  return data ? <EntityRiskPageView d={data} /> : <PageSkeleton />;
}

function EntityRiskPageView({ d }: { d: DashboardData }) {
  const { entityRisk } = d;
  const { entityId = "" } = useParams();
  const entity = entityRisk[entityId as keyof DashboardData["entityRisk"]];

  if (!entity) {
    return (
      <PageHeader title="Entity not found" description="Select an entity from the exposure heatmap on the dashboard." />
    );
  }

  return (
    <>
      <PageHeader
        title={entity.name}
        description="Exception trend, root causes, aging distribution, and historical match rate."
        actions={
          <Button component={RouterLink} to="/dashboard" variant="outlined">
            Back to dashboard
          </Button>
        }
      />
      <Box sx={{ display: "grid", gridTemplateColumns: { xs: "1fr", md: "1fr 1fr" }, gap: 3 }}>
        <Panel title="Exposure">
          <Typography sx={{ fontFamily: 'var(--font-mono)', fontSize: 28, fontWeight: 700 }}>
            {entity.exposure}
          </Typography>
          <Typography sx={{ color: "text.secondary" }}>Unmatched financial risk</Typography>
        </Panel>
        <Panel title="Historical match rate">
          <Typography sx={{ fontFamily: 'var(--font-mono)', fontSize: 28, fontWeight: 700 }}>
            {entity.matchRate}
          </Typography>
          <Stack direction="row" alignItems="flex-end" spacing={0.75} sx={{ height: 72, mt: 1.5 }}>
            {entity.trend.map((point, index) => (
              <Box
                key={index}
                sx={{
                  flex: 1,
                  height: `${((point - 80) / 20) * 100}%`,
                  minHeight: 10,
                  bgcolor: "primary.main",
                  borderRadius: "4px 4px 0 0",
                }}
              />
            ))}
          </Stack>
        </Panel>
        <Panel title="Aging distribution">
          <Stack spacing={1.25}>
            {entity.aging.map((bucket) => (
              <Box key={bucket.bucket}>
                <Stack direction="row" justifyContent="space-between">
                  <Typography sx={{ fontSize: 12 }}>{bucket.bucket}</Typography>
                  <Typography sx={{ fontSize: 12, fontWeight: 700 }}>{bucket.count}</Typography>
                </Stack>
                <LinearProgress variant="determinate" value={Math.min(100, bucket.count)} sx={{ height: 7, borderRadius: 99 }} />
              </Box>
            ))}
          </Stack>
        </Panel>
        <Panel title="Root causes">
          <Stack spacing={1.25}>
            {entity.causes.map((cause) => (
              <Box key={cause.label}>
                <Stack direction="row" justifyContent="space-between">
                  <Typography sx={{ fontSize: 12 }}>{cause.label}</Typography>
                  <Typography sx={{ fontSize: 12, fontWeight: 700 }}>{cause.share}%</Typography>
                </Stack>
                <LinearProgress variant="determinate" value={cause.share} sx={{ height: 7, borderRadius: 99 }} />
              </Box>
            ))}
          </Stack>
        </Panel>
      </Box>
    </>
  );
}
