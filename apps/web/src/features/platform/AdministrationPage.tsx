import { useState } from "react";
import { Box, Button, Chip, Stack, Switch, Tab, Tabs, Typography } from "@mui/material";
import { api } from "../../api/services";
import { useQuery } from "../../api/useQuery";
import type { AppUser, LegalEntity } from "../../api/types";
import { Panel, StatusPill } from "../../components/common/Panel";
import { DataTable, KeyValue, Page, StatGrid, glass, mono, useToast } from "../../components/common/Blocks";

const userTone = { Active: "ok", Invited: "warn", Disabled: "crit" } as const;

export function AdministrationPage() {
  const { data, loading } = useQuery(api.admin.all);
  const [tab, setTab] = useState(0);
  const { toast, toastNode } = useToast();
  return (
    <Page title="Administration" description="Tenant settings, users and roles, legal entities, and security configuration." loading={loading}
      actions={<Button variant="contained" onClick={() => toast("Invitation sent")}>Invite user</Button>}>
      {data ? (
        <>
          <StatGrid items={[
            { label: "Users", value: String(data.users.length) },
            { label: "MFA coverage", value: `${Math.round((data.users.filter((u) => u.mfa).length / data.users.length) * 100)}%`, tone: "warn" },
            { label: "Roles", value: String(data.roles.length) },
            { label: "Legal entities", value: String(data.entities.length) },
          ]} />
          <Tabs value={tab} onChange={(_, v) => setTab(v)}>
            <Tab label="Users" /><Tab label="Roles & permissions" /><Tab label="Legal entities" /><Tab label="Security" />
          </Tabs>
          {tab === 0 ? (
            <DataTable<AppUser> rows={data.users} rowKey={(u) => u.email} columns={[
              { key: "n", header: "Name", render: (u) => <><Typography sx={{ fontSize: 12, fontWeight: 600 }}>{u.name}</Typography><Typography sx={{ fontSize: 11, color: "text.secondary" }}>{u.email}</Typography></> },
              { key: "r", header: "Role", render: (u) => u.role },
              { key: "e", header: "Entities", render: (u) => u.entities.join(", ") },
              { key: "s", header: "Status", render: (u) => <StatusPill label={u.status} tone={userTone[u.status]} /> },
              { key: "m", header: "MFA", render: (u) => (u.mfa ? "On" : <Typography sx={{ fontSize: 12, color: "error.main", fontWeight: 600 }}>Off</Typography>) },
              { key: "l", header: "Last login", render: (u) => u.lastLogin },
              { key: "a", header: "", render: (u) => <Button size="small" onClick={() => toast(`Editing ${u.name}`)}>Edit</Button> },
            ]} />
          ) : tab === 1 ? (
            <Box sx={{ display: "grid", gridTemplateColumns: { xs: "1fr", md: "1fr 1fr", xl: "repeat(3, 1fr)" }, gap: 2 }}>
              {data.roles.map((r) => (
                <Box key={r.role} sx={{ ...glass, p: 2 }}>
                  <Stack direction="row" justifyContent="space-between"><Typography sx={{ fontWeight: 700, fontSize: 13 }}>{r.role}</Typography><Chip size="small" label={`${r.users} users`} /></Stack>
                  <Stack direction="row" spacing={0.5} flexWrap="wrap" useFlexGap sx={{ mt: 1.25 }}>
                    {r.permissions.map((p) => <Chip key={p} size="small" variant="outlined" label={p} />)}
                  </Stack>
                </Box>
              ))}
            </Box>
          ) : tab === 2 ? (
            <DataTable<LegalEntity> rows={data.entities} rowKey={(e) => e.code} columns={[
              { key: "c", header: "Code", render: (e) => <b style={mono}>{e.code}</b> },
              { key: "n", header: "Name", render: (e) => e.name },
              { key: "co", header: "Country", render: (e) => e.country },
              { key: "cu", header: "Currency", render: (e) => e.currency },
              { key: "o", header: "Recon owner", render: (e) => e.owner },
            ]} />
          ) : (
            <Box sx={{ display: "grid", gridTemplateColumns: { xs: "1fr", md: "1fr 1fr" }, gap: 2.5 }}>
              <Panel title="Identity">
                <KeyValue label="SSO provider" value="Okta (OIDC)" />
                <KeyValue label="SCIM provisioning" value="Enabled" />
                <KeyValue label="Session timeout" value="30 minutes" />
                <KeyValue label="Enforce MFA" value={<Switch size="small" defaultChecked onChange={() => toast("MFA policy updated")} />} />
              </Panel>
              <Panel title="Tenant & data">
                <KeyValue label="Tenant" value="ufme-demo (EU-West)" />
                <KeyValue label="Encryption" value="AES-256, customer-managed key" />
                <KeyValue label="IP allowlist" value="3 ranges" />
                <KeyValue label="Data residency" value="EU" />
              </Panel>
            </Box>
          )}
        </>
      ) : null}
      {toastNode}
    </Page>
  );
}
