import { useEffect, useState } from "react";
import { Avatar, Box, ListItemText, Menu, MenuItem, Stack, Typography } from "@mui/material";
import ExpandMore from "@mui/icons-material/ExpandMore";
import { actingUser, api } from "../../api/services";
import type { Actor } from "../../api/types";

const initials = (name: string) =>
  name
    .split(" ")
    .map((p) => p[0])
    .join("")
    .slice(0, 2)
    .toUpperCase();

/** Demo identity switcher (until SSO). The server enforces roles and segregation of duties per user. */
export function ActingAs() {
  const [me, setMe] = useState<Actor | null>(null);
  const [all, setAll] = useState<Actor[]>([]);
  const [anchor, setAnchor] = useState<HTMLElement | null>(null);

  useEffect(() => {
    api.workflow.me().then(setMe).catch(() => setMe(null));
    api.workflow.actors().then(setAll).catch(() => setAll([]));
  }, []);

  const pick = (a: Actor) => {
    setAnchor(null);
    if (a.email === me?.email) return;
    actingUser.set(a.email);
    window.location.reload(); // every screen re-reads with the new user's permissions
  };

  return (
    <>
      <Stack
        direction="row"
        alignItems="center"
        spacing={1}
        onClick={(e) => setAnchor(e.currentTarget)}
        sx={{ cursor: "pointer", px: 0.75, py: 0.4, borderRadius: "8px", "&:hover": { bgcolor: "var(--bg-muted)" } }}
        title="Switch the user you're acting as"
      >
        <Avatar sx={{ width: 26, height: 26, bgcolor: "var(--bg-muted)", color: "text.primary", border: "1px solid var(--border-strong)", fontSize: 11, fontWeight: 600 }}>
          {me ? initials(me.name) : "··"}
        </Avatar>
        <Box sx={{ lineHeight: 1.1 }}>
          <Typography sx={{ fontWeight: 500, fontSize: 12.5 }}>{me?.name ?? "Loading"}</Typography>
          <Typography sx={{ fontSize: 10, color: "var(--text-muted)", fontFamily: "var(--font-mono)" }}>{me?.role.toUpperCase() ?? ""}</Typography>
        </Box>
        <ExpandMore sx={{ fontSize: 16, color: "text.secondary" }} />
      </Stack>
      <Menu anchorEl={anchor} open={Boolean(anchor)} onClose={() => setAnchor(null)} anchorOrigin={{ vertical: "bottom", horizontal: "right" }} transformOrigin={{ vertical: "top", horizontal: "right" }}>
        <Typography sx={{ px: 2, pt: 1, pb: 0.5, fontSize: 10.5, fontFamily: "var(--font-mono)", color: "var(--text-muted)" }}>ACT AS</Typography>
        {all.map((a) => (
          <MenuItem key={a.email} selected={a.email === me?.email} onClick={() => pick(a)} sx={{ gap: 1.25, minWidth: 260 }}>
            <Avatar sx={{ width: 24, height: 24, fontSize: 10, bgcolor: "var(--bg-muted)", color: "text.primary" }}>{initials(a.name)}</Avatar>
            <ListItemText
              primary={a.name}
              secondary={`${a.role} · ${a.entities.join(", ")}`}
              primaryTypographyProps={{ fontSize: 13 }}
              secondaryTypographyProps={{ fontSize: 11 }}
            />
          </MenuItem>
        ))}
      </Menu>
    </>
  );
}
