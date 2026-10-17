import { Chip, Stack, Typography } from "@mui/material";
import { api } from "../../api/services";
import { useQuery } from "../../api/useQuery";
import type { FeatureDef } from "../../api/types";
import { DataTable, Meter, Page, StatGrid, mono } from "../../components/common/Blocks";

export function FeaturesPage() {
  const { data = [], loading } = useQuery(api.data.features);
  return (
    <Page title="Feature store" description="Versioned features shared by the rule engine, optimizer, and ranking models — computed once, consistent online and offline." loading={loading}>
      <StatGrid items={[
        { label: "Features", value: String(data.length) },
        { label: "Groups", value: String(new Set(data.map((f) => f.group)).size) },
        { label: "Real-time", value: String(data.filter((f) => f.freshness === "Real-time").length), tone: "ok" },
        { label: "Avg coverage", value: `${(data.reduce((s, f) => s + f.coverage, 0) / Math.max(data.length, 1)).toFixed(1)}%`, tone: "ok" },
      ]} />
      <DataTable<FeatureDef> rows={data} rowKey={(f) => f.name} columns={[
        { key: "n", header: "Feature", render: (f) => <Typography sx={{ ...mono, fontSize: 12, fontWeight: 700 }}>{f.name}</Typography> },
        { key: "g", header: "Group", render: (f) => f.group },
        { key: "t", header: "Type", render: (f) => <span style={mono}>{f.type}</span> },
        { key: "v", header: "Version", render: (f) => f.version },
        { key: "u", header: "Used by", render: (f) => <Stack direction="row" spacing={0.5}>{f.usedBy.map((u) => <Chip key={u} size="small" label={u} />)}</Stack> },
        { key: "fr", header: "Freshness", render: (f) => f.freshness },
        { key: "c", header: "Coverage", render: (f) => <Stack direction="row" spacing={1} alignItems="center"><Meter value={f.coverage} tone={f.coverage > 98 ? "ok" : "warn"} /><span style={mono}>{f.coverage}%</span></Stack> },
      ]} />
    </Page>
  );
}
