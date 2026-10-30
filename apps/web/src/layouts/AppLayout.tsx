import { useState, type MouseEvent } from "react";
import { NavLink, Outlet, useLocation, useNavigate } from "react-router-dom";
import { Badge, Box, IconButton, ListItemText, Menu, MenuItem, Stack, Typography } from "@mui/material";
import DarkModeOutlinedIcon from "@mui/icons-material/DarkModeOutlined";
import ExpandMore from "@mui/icons-material/ExpandMore";
import LightModeOutlinedIcon from "@mui/icons-material/LightModeOutlined";
import NotificationsNoneOutlinedIcon from "@mui/icons-material/NotificationsNoneOutlined";
import { useDispatch, useSelector } from "react-redux";
import { navItems, type NavItem } from "../navigation/navConfig";
import { ActivityTicker } from "../components/shell/ActivityTicker";
import { CopilotDock } from "../components/shell/CopilotDock";
import { Logo } from "../components/common/Logo";
import { ActingAs } from "../components/shell/ActingAs";
import { toggleColorMode } from "../store/uiSlice";
import type { RootState } from "../store";

function isPathActive(pathname: string, to?: string, childrenTo: string[] = []) {
  const hit = (p: string) => pathname === p || (p !== "/exceptions" && pathname.startsWith(`${p}/`));
  return Boolean(to && hit(to)) || childrenTo.some(hit);
}

const tab = (active: boolean) => ({
  display: "inline-flex",
  alignItems: "center",
  gap: 0.5,
  height: 36,
  px: 1.25,
  borderRadius: "4px",
  border: 0,
  cursor: "pointer",
  font: "inherit",
  fontSize: 14.5,
  fontWeight: active ? 500 : 400,
  textDecoration: "none",
  whiteSpace: "nowrap" as const,
  color: active ? "var(--bg-surface)" : "var(--text-primary)",
  bgcolor: active ? "var(--text-primary)" : "transparent",
  "&:hover": { bgcolor: active ? "var(--text-primary)" : "var(--bg-muted)" },
  "&:focus-visible": { outline: "2px solid var(--brand-indigo)", outlineOffset: 2 },
});

// The daily areas are tabs; the platform areas live under "More" so the bar stays one line.
const PRIMARY = new Set(["Dashboard", "Reconciliation", "Exceptions", "Cases", "Rules & Policies", "Intelligence", "Audit & SOX"]);
const primaryItems = navItems.filter((i) => PRIMARY.has(i.label));
const moreItem: NavItem = {
  label: "More",
  icon: navItems[0].icon,
  description: "Platform areas",
  children: navItems
    .filter((i) => !PRIMARY.has(i.label))
    .flatMap((i) =>
      i.children
        ? i.children.map((c) => ({ ...c, label: `${i.label} · ${c.label}` }))
        : [{ label: i.label, to: i.to!, description: i.description }],
    ),
};

/** Top navigation: one tab per area; areas with several screens open a menu describing each. */
function TopNav() {
  const { pathname } = useLocation();
  const navigate = useNavigate();
  const [open, setOpen] = useState<{ item: NavItem; anchor: HTMLElement } | null>(null);

  return (
    <Box component="nav" aria-label="Main" sx={{ display: "flex", gap: 0.25, flexWrap: "wrap", minWidth: 0 }}>
      {[...primaryItems, moreItem].map((item) => {
        const active = isPathActive(pathname, item.to, item.children?.map((c) => c.to) ?? []);
        if (!item.children) {
          return (
            <Box key={item.label} component={NavLink} to={item.to!} sx={tab(active)}>
              {item.label}
            </Box>
          );
        }
        return (
          <Box
            key={item.label}
            component="button"
            type="button"
            aria-haspopup="menu"
            aria-expanded={open?.item.label === item.label}
            onClick={(e: MouseEvent<HTMLElement>) => setOpen({ item, anchor: e.currentTarget })}
            sx={tab(active)}
          >
            {item.label}
            {item.badge ? (
              <Box component="span" sx={{ fontFamily: "var(--font-mono)", fontSize: 11, px: 0.6, borderRadius: "9999px", bgcolor: "var(--amber-soft)", color: "var(--text-primary)" }}>
                {item.badge}
              </Box>
            ) : null}
            <ExpandMore sx={{ fontSize: 16 }} />
          </Box>
        );
      })}
      <Menu
        anchorEl={open?.anchor}
        open={Boolean(open)}
        onClose={() => setOpen(null)}
        anchorOrigin={{ vertical: "bottom", horizontal: "left" }}
        slotProps={{ paper: { sx: { minWidth: 320, maxWidth: 380 } } }}
      >
        {open?.item.children?.map((child) => (
          <MenuItem
            key={child.to}
            selected={pathname === child.to}
            onClick={() => {
              setOpen(null);
              navigate(child.to);
            }}
            sx={{ alignItems: "flex-start", py: 1.25, whiteSpace: "normal" }}
          >
            <ListItemText
              primary={child.label}
              secondary={child.description}
              primaryTypographyProps={{ fontSize: 15, fontWeight: 500, color: "text.primary" }}
              secondaryTypographyProps={{ fontSize: 12.5, color: "text.secondary", mt: 0.25 }}
            />
          </MenuItem>
        ))}
      </Menu>
    </Box>
  );
}

export function AppLayout() {
  const { pathname } = useLocation();
  const dispatch = useDispatch();
  const colorMode = useSelector((state: RootState) => state.ui.colorMode);

  return (
    <Box className="ufme-shell">
      <Box
        component="header"
        className="ufme-header"
        sx={{ display: "flex", alignItems: "center", gap: { xs: 1.5, md: 3 }, px: { xs: 2, md: 4 }, py: { xs: 1, md: 0 }, flexWrap: { xs: "wrap", md: "nowrap" }, zIndex: 10 }}
      >
        <NavLink to="/dashboard" aria-label="ufme home" style={{ textDecoration: "none" }}>
          <Logo />
        </NavLink>
        <Box sx={{ flex: 1, minWidth: 0 }}>
          <TopNav />
        </Box>
        <Stack direction="row" alignItems="center" spacing={1.5}>
          <Typography sx={{ fontFamily: "var(--font-mono)", fontSize: 12.5, color: "text.secondary", display: { xs: "none", lg: "block" } }}>
            Q3-2026
          </Typography>
          <IconButton size="small" onClick={() => dispatch(toggleColorMode())} aria-label={colorMode === "dark" ? "Switch to light mode" : "Switch to dark mode"}>
            {colorMode === "dark" ? <LightModeOutlinedIcon fontSize="small" /> : <DarkModeOutlinedIcon fontSize="small" />}
          </IconButton>
          <IconButton size="small" aria-label="Notifications, 8 new">
            <Badge badgeContent={8} color="warning">
              <NotificationsNoneOutlinedIcon fontSize="small" />
            </Badge>
          </IconButton>
          <ActingAs />
        </Stack>
      </Box>

      <Box className="ufme-main" component="main">
        <Box key={pathname} className="page-enter" sx={{ display: "flex", flexDirection: "column", gap: 3, minHeight: "100%" }}>
          <Outlet />
        </Box>
      </Box>
      <CopilotDock />
      <ActivityTicker />
    </Box>
  );
}
