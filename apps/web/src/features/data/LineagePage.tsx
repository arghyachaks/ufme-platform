import { useState } from "react";
import { Box, MenuItem, Stack, TextField, Typography } from "@mui/material";
import { api } from "../../api/services";
import { useQuery } from "../../api/useQuery";
import { Page, glass, mono } from "../../components/common/Blocks";

const dot = { ok: "success.main", warn: "warning.main", crit: "error.main" } as const;

export function LineagePage() {
  const { data: ids = [], loading } = useQuery(api.data.lineageIds);
  const [txn, setTxn] = useState("TXN-US01-778120");
  const { data: steps = [] } = useQuery(() => api.data.lineage(txn), [txn]);
  return (
    <Page title="Lineage" description="Trace a transaction from source extraction through quality, enrichment, rules, optimization, and ranking to the final decision." loading={loading}
      actions={
        <TextField select size="small" label="Transaction" value={txn} onChange={(e) => setTxn(e.target.value)} sx={{ minWidth: 220 }}>
          {ids.map((id) => <MenuItem key={id} value={id}>{id}</MenuItem>)}
        </TextField>
      }>
      <Box sx={{ ...glass, p: 3 }}>
        <Stack>
          {steps.map((s, i) => (
            <Stack key={s.stage} direction="row" spacing={2}>
              <Stack alignItems="center" sx={{ width: 16 }}>
                <Box sx={{ width: 12, height: 12, borderRadius: "50%", bgcolor: dot[s.status], mt: 0.5, flexShrink: 0 }} />
                {i < steps.length - 1 ? <Box sx={{ width: 2, flex: 1, bgcolor: "divider", my: 0.5 }} /> : null}
              </Stack>
              <Box sx={{ pb: 2.5, flex: 1 }}>
                <Stack direction={{ xs: "column", sm: "row" }} justifyContent="space-between">
                  <Typography sx={{ fontSize: 13, fontWeight: 700 }}>{s.stage} <Typography component="span" sx={{ fontSize: 12, color: "text.secondary", fontWeight: 400 }}>· {s.system}</Typography></Typography>
                  <Typography sx={{ ...mono, fontSize: 11, color: "text.secondary" }}>{s.at}</Typography>
                </Stack>
                <Typography sx={{ fontSize: 12, mt: 0.25 }}>{s.detail}</Typography>
              </Box>
            </Stack>
          ))}
        </Stack>
      </Box>
    </Page>
  );
}
