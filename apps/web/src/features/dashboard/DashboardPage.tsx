import matchingArt from "../../assets/matching-static.svg";
import { useState } from "react";
import { Link as RouterLink } from "react-router-dom";
import { Box, Button, LinearProgress, Stack, Table, TableBody, TableCell, TableHead, TableRow, Typography } from "@mui/material";
import { Panel, StatusPill } from "../../components/common/Panel";
import { workspaceApi, type DashboardData } from "../../api/services";
import { useQuery } from "../../api/useQuery";
import { PageSkeleton } from "../../components/common/Blocks";

export function DashboardPage() {
  const { data } = useQuery(workspaceApi.dashboard);
  return data ? <DashboardPageView d={data} /> : <PageSkeleton />;
}

function DashboardPageView({ d }: { d: DashboardData }) {
  const { agentFlow, agents, closeCompletion, closeDays, controlsAtRisk, exposureTiles, forecast, highRiskExceptions, kpiGroups, learning, rootCauses, sla, trendSeries, workQueue, workflowFunnel } = d;
  const [range, setRange] = useState<keyof DashboardData["trendSeries"]>("7D");
  const trend = trendSeries[range];
  const maxTrend = Math.max(...trend);

  return (
    <Stack spacing={3} className="no-motion">
      <Box
        component="section"
        aria-label="Today"
        sx={{
          bgcolor: "var(--emerald-soft)",
          borderRadius: "2px",
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          flexWrap: "wrap",
          gap: 2,
          px: { xs: 2.5, md: 4 },
          py: 2,
        }}
      >
        <Stack spacing={0.75} sx={{ minWidth: 0, flex: "1 1 420px" }}>
          <Typography sx={{ fontFamily: "var(--font-mono)", fontSize: 12, letterSpacing: "0.04em", textTransform: "uppercase" }}>
            Q3-2026 close · {closeCompletion}% complete
          </Typography>
          <Typography variant="h4" component="h1" sx={{ fontSize: "clamp(24px, 2.2vw, 32px)" }}>
            Every intercompany line, matched and explained.
          </Typography>
        </Stack>
        <Stack direction="row" alignItems="center" gap={3}>
          <Box component="img" src={matchingArt} alt="" sx={{ height: 72, display: { xs: "none", lg: "block" } }} />
          <Stack direction="row" gap={1.5} flexWrap="wrap">
            <Button variant="contained" component={RouterLink} to="/reconciliation/review">Open review queue</Button>
            <Button variant="outlined" component={RouterLink} to="/reconciliation/runs">Run reconciliation</Button>
          </Stack>
        </Stack>
      </Box>
      <Box sx={{ display: "grid", gridTemplateColumns: { xs: "minmax(0, 1fr)", xl: "minmax(0, 1fr) minmax(0, 2fr)" }, gap: 3, "& > *": { minWidth: 0 } }}>
        <Panel title="Period close" action={<Typography sx={{ fontSize: 11, color: "text.secondary" }}>Q3-2026</Typography>}>
          <Typography className="display" sx={{ fontSize: "clamp(32px, 2.6vw, 40px)", lineHeight: 1 }}>
            {`${closeCompletion}%`}
          </Typography>
          <Typography sx={{ fontSize: 12, color: "text.secondary", mb: 1.5 }}>Close completion</Typography>
          <LinearProgress variant="determinate" value={closeCompletion} sx={{ height: 6, borderRadius: 99, mb: 1.5, mt: 1.5, "& .MuiLinearProgress-bar": { background: "var(--brand-indigo)" } }} />
          <Stack direction="row" spacing={1}>
            {closeDays.map((day) => (
              <Box
                key={day.label}
                sx={{
                  flex: 1,
                  textAlign: "center",
                  py: 0.75,
                  borderRadius: 1,
                  fontSize: 11,
                  fontWeight: 700,
                  bgcolor: day.done ? "var(--emerald-soft)" : "var(--bg-muted)",
                  color: day.done ? "var(--brand-emerald)" : "text.secondary",
                  border: "1px solid",
                  borderColor: "divider",
                }}
              >
                {day.label}
              </Box>
            ))}
          </Stack>
        </Panel>

        <Box sx={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))", gap: 3, "& > *": { minWidth: 0 } }}>
          {kpiGroups.map((group) => (
            <Panel key={group.title} title={group.title}>
              <Stack spacing={1.25}>
                {group.items.map((item) => (
                  <Box key={item.label}>
                    <Typography sx={{ fontFamily: "var(--font-mono)", fontSize: 10, color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.08em" }}>
                      {item.label}
                    </Typography>
                    <Typography className="display" sx={{ fontSize: "clamp(17px, 1.35vw, 21px)", lineHeight: 1.2, whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>
                      {item.value}
                    </Typography>
                    <Typography sx={{ fontSize: 11, color: "text.secondary" }}>{item.hint}</Typography>
                  </Box>
                ))}
              </Stack>
            </Panel>
          ))}
        </Box>
      </Box>

      <Panel title="My work queue" action={<Typography sx={{ fontSize: 11, color: "text.secondary" }}>Start here</Typography>}>
        <Box sx={{ display: "grid", gridTemplateColumns: { xs: "1fr 1fr", lg: "repeat(4, 1fr)" }, gap: 2 }}>
          {workQueue.map((item) => (
            <Button
              key={item.label}
              component={RouterLink}
              to={item.to}
              sx={{
                display: "block",
                textAlign: "left",
                p: 1.5,
                border: "1px solid",
                borderColor: "divider",
                bgcolor: "var(--bg-muted)",
                color: "text.primary",
              }}
            >
              <Typography className="display" sx={{ fontSize: "clamp(20px, 1.6vw, 24px)", lineHeight: 1.1, color: item.tone === "crit" ? "error.main" : item.tone === "warn" ? "warning.main" : "success.main" }}>
                {String(item.count)}
              </Typography>
              <Typography sx={{ fontSize: 12, fontWeight: 600 }}>{item.label}</Typography>
            </Button>
          ))}
        </Box>
      </Panel>

      <Panel
        title="Reconciliation Workflow Funnel"
        action={<Typography sx={{ fontFamily: 'var(--font-mono)', fontSize: 11, color: "secondary.main" }}>Finance operations lifecycle</Typography>}
      >
        <Box sx={{ position: "relative", display: "flex", alignItems: "center", justifyContent: "space-between", py: 2.5, gap: 0.5 }}>
          <Box className="pipeline-track">
            <Box className="pipeline-particle" />
          </Box>
          {workflowFunnel.map((node) => (
            <Box
              key={node.label}
              className="glass"
              sx={{
                position: "relative",
                zIndex: 2,
                px: 1,
                py: 0.9,
                textAlign: "center",
                minWidth: 78,
                borderRadius: 2,
              }}
            >
              <Typography sx={{ fontFamily: 'var(--font-mono)', fontSize: 13, fontWeight: 700 }}>{node.value}</Typography>
              <Typography sx={{ fontSize: 9, fontWeight: 700, textTransform: "uppercase", color: "text.secondary" }}>
                {node.label}
              </Typography>
            </Box>
          ))}
        </Box>
      </Panel>

      <Box sx={{ display: "grid", gridTemplateColumns: { xs: "1fr", lg: "1.35fr 1fr" }, gap: 3 }}>
        <Panel
          title="High Risk Exceptions"
          action={
            <Button component={RouterLink} to="/exceptions" size="small" sx={{ fontSize: 11 }}>
              Sorted by exposure
            </Button>
          }
        >
          <Table size="small">
            <TableHead>
              <TableRow>
                <TableCell>Case</TableCell>
                <TableCell>Impact</TableCell>
                <TableCell>Entity</TableCell>
                <TableCell>Owner</TableCell>
                <TableCell>Due</TableCell>
                <TableCell>Aging</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {highRiskExceptions.map((row) => (
                <TableRow key={row.id} hover>
                  <TableCell>
                    <Typography sx={{ fontFamily: 'var(--font-mono)', fontWeight: 700, fontSize: 12 }}>{row.id}</Typography>
                    <StatusPill label={row.severity} tone={row.severity === "CRITICAL" ? "crit" : "warn"} />
                  </TableCell>
                  <TableCell sx={{ fontFamily: 'var(--font-mono)', fontWeight: 700, color: "error.main" }}>
                    {row.impact}
                  </TableCell>
                  <TableCell>{row.entity}</TableCell>
                  <TableCell>{row.owner}</TableCell>
                  <TableCell>{row.due}</TableCell>
                  <TableCell sx={{ fontFamily: 'var(--font-mono)' }}>{row.age}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </Panel>

        <Panel title="Financial Exposure Heatmap" action={<Typography sx={{ fontSize: 11, color: "text.secondary" }}>Click entity to drill down</Typography>}>
          <Box sx={{ display: "grid", gridTemplateColumns: "2fr 1fr", gridTemplateRows: "1fr 1fr", gap: 0.75, height: 200 }}>
            {exposureTiles.map((tile, index) => (
              <Box
                key={tile.id}
                component={RouterLink}
                to={`/risk/${tile.id}`}
                sx={{
                  textDecoration: "none",
                  borderRadius: "6px",
                  p: 1.5,
                  display: "flex",
                  flexDirection: "column",
                  justifyContent: "space-between",
                  gridRow: index === 0 ? "1 / 3" : "auto",
                  ...(tile.tone === "crit"
                    ? { bgcolor: "var(--crimson-soft)", color: "var(--brand-crimson)", border: "1px solid color-mix(in srgb, var(--brand-crimson) 28%, transparent)" }
                    : tile.tone === "warn"
                      ? { bgcolor: "var(--amber-soft)", color: "var(--brand-amber)", border: "1px solid color-mix(in srgb, var(--brand-amber) 28%, transparent)" }
                      : { bgcolor: "var(--emerald-soft)", color: "var(--brand-emerald)", border: "1px solid color-mix(in srgb, var(--brand-emerald) 28%, transparent)" }),
                }}
              >
                <Box>
                  <Typography sx={{ fontFamily: 'var(--font-mono)', fontSize: index === 0 ? 20 : 14, fontWeight: 700 }}>
                    {tile.amount}
                  </Typography>
                  <Typography sx={{ fontSize: 12, fontWeight: 600 }}>{tile.entity}</Typography>
                </Box>
                <Typography sx={{ fontSize: 10, opacity: 0.85 }}>{tile.cause}</Typography>
              </Box>
            ))}
          </Box>
        </Panel>
      </Box>

      <Box sx={{ display: "grid", gridTemplateColumns: { xs: "1fr", lg: "1fr 1fr" }, gap: 3 }}>
        <Panel title="Top Exception Causes">
          <Stack spacing={1.25}>
            {rootCauses.map((cause) => (
              <Box key={cause.label}>
                <Stack direction="row" justifyContent="space-between" sx={{ mb: 0.4 }}>
                  <Typography sx={{ fontSize: 12 }}>{cause.label}</Typography>
                  <Typography sx={{ fontSize: 12, fontWeight: 700 }}>{cause.share}%</Typography>
                </Stack>
                <LinearProgress variant="determinate" value={cause.share} sx={{ height: 7, borderRadius: 99 }} />
              </Box>
            ))}
          </Stack>
        </Panel>

        <Panel
          title="Match Rate Trend & Forecast"
          action={
            <Stack direction="row" spacing={0.5}>
              {(Object.keys(trendSeries) as Array<keyof DashboardData["trendSeries"]>).map((key) => (
                <Button key={key} size="small" variant={range === key ? "contained" : "text"} onClick={() => setRange(key)} sx={{ minWidth: 0, px: 1, fontSize: 11 }}>
                  {key}
                </Button>
              ))}
            </Stack>
          }
        >
          <Stack direction="row" alignItems="flex-end" spacing={0.75} sx={{ height: 92, mb: 1.5 }}>
            {trend.map((point, index) => (
              <Box key={index} sx={{ flex: 1, bgcolor: "primary.main", opacity: 0.35 + (point / maxTrend) * 0.65, height: `${((point - 90) / 10) * 100}%`, minHeight: 12, borderRadius: "4px 4px 0 0" }} />
            ))}
          </Stack>
          <Typography sx={{ fontSize: 12, fontWeight: 700, mb: 0.75 }}>Expected tomorrow</Typography>
          <Stack direction="row" spacing={2}>
            <ForecastStat label="Exceptions" value={forecast.exceptions} />
            <ForecastStat label="Exposure" value={forecast.exposure} />
            <ForecastStat label="Match rate" value={forecast.matchRate} />
          </Stack>
        </Panel>
      </Box>

      <Box sx={{ display: "grid", gridTemplateColumns: { xs: "1fr", lg: "1fr 1fr" }, gap: 3 }}>
        <Panel title="SLA Dashboard">
          <Stack direction="row" spacing={1}>
            {sla.map((item) => (
              <Box key={item.label} sx={{ flex: 1, p: 1.25, borderRadius: 1, border: "1px solid", borderColor: "divider" }}>
                <Typography className="display" sx={{ fontSize: "clamp(20px, 1.6vw, 24px)", lineHeight: 1.1 }}>{String(item.count)}</Typography>
                <StatusPill label={item.label} tone={item.tone} />
              </Box>
            ))}
          </Stack>
        </Panel>
        <Panel title="Controls at Risk">
          <Stack spacing={1}>
            {controlsAtRisk.map((item) => (
              <Stack key={item.label} direction="row" justifyContent="space-between" alignItems="center" sx={{ p: 1, border: "1px solid", borderColor: "var(--glass-border)", borderRadius: "2px" }}>
                <Typography sx={{ fontSize: 13 }}>{item.label}</Typography>
                <StatusPill label={String(item.count)} tone={item.tone} />
              </Stack>
            ))}
          </Stack>
        </Panel>
      </Box>

      <Box sx={{ display: "grid", gridTemplateColumns: { xs: "1fr", lg: "1.4fr 1fr" }, gap: 3 }}>
        <Panel title="Matching pipeline" action={<StatusPill label="RUNNING" tone="ok" />}>
          <Stack direction="row" alignItems="center" justifyContent="space-between" sx={{ mb: 2 }}>
            {agentFlow.map((name, index) => (
              <Stack key={name} direction="row" alignItems="center" spacing={1} sx={{ flex: 1 }}>
                <Box sx={{ px: 1.25, py: 0.75, bgcolor: "var(--indigo-soft)", color: "primary.main", borderRadius: 1, fontSize: 11, fontWeight: 700, whiteSpace: "nowrap" }}>
                  {name}
                </Box>
                {index < agentFlow.length - 1 ? <Typography sx={{ color: "text.secondary" }}>→</Typography> : null}
              </Stack>
            ))}
          </Stack>
          <Box sx={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 2 }}>
            {agents.map((agent) => (
              <Box key={agent.name} sx={{ p: 1.25, border: "1px solid", borderColor: "var(--glass-border)", borderRadius: "2px", bgcolor: "var(--bg-muted)" }}>
                <Typography sx={{ fontSize: 12, fontWeight: 700, color: "primary.main", mb: 0.75 }}>{agent.name}</Typography>
                <Metric label="Workload" value={agent.workload} />
                <Metric label="Precision" value={agent.precision} />
                <Metric label="Status" value={agent.status} />
              </Box>
            ))}
          </Box>
        </Panel>

        <Panel title="Accuracy over time">
          <Stack spacing={1}>
            {learning.map((item) => (
              <Stack key={item.label} direction="row" justifyContent="space-between" sx={{ py: 0.75, borderBottom: "1px solid", borderColor: "divider" }}>
                <Typography sx={{ fontSize: 13 }}>{item.label}</Typography>
                <Typography sx={{ fontFamily: 'var(--font-mono)', fontWeight: 700 }}>{item.value}</Typography>
              </Stack>
            ))}
          </Stack>
        </Panel>
      </Box>
    </Stack>
  );
}

function ForecastStat({ label, value }: { label: string; value: string }) {
  return (
    <Box>
      <Typography sx={{ fontSize: 11, color: "text.secondary" }}>{label}</Typography>
      <Typography sx={{ fontFamily: 'var(--font-mono)', fontWeight: 700 }}>{value}</Typography>
    </Box>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <Stack direction="row" justifyContent="space-between" sx={{ fontSize: 11, mb: 0.4 }}>
      <span>{label}</span>
      <Box component="strong" sx={{ fontFamily: 'var(--font-mono)' }}>
        {value}
      </Box>
    </Stack>
  );
}
