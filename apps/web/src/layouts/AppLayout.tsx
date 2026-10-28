import type { ReactNode } from "react";
import { useEffect, useMemo, useState } from "react";
import { NavLink, Outlet, useLocation } from "react-router-dom";
import { Badge, Box, Collapse, IconButton, InputBase, Stack, Typography } from "@mui/material";
import DarkModeOutlinedIcon from "@mui/icons-material/DarkModeOutlined";
import ExpandMore from "@mui/icons-material/ExpandMore";
import LightModeOutlinedIcon from "@mui/icons-material/LightModeOutlined";
import NotificationsNoneOutlinedIcon from "@mui/icons-material/NotificationsNoneOutlined";
import SearchIcon from "@mui/icons-material/Search";
import { useDispatch, useSelector } from "react-redux";
import { navItems } from "../navigation/navConfig";
import { ActivityTicker } from "../components/shell/ActivityTicker";
import { CopilotDock } from "../components/shell/CopilotDock";
import { Logo } from "../components/common/Logo";
import { ActingAs } from "../components/shell/ActingAs";
import { toggleColorMode } from "../store/uiSlice";
import type { RootState } from "../store";

function isPathActive(pathname: string, to?: string, childrenTo: string[] = []) {
  if (to && pathname === to) {
    return true;
  }
  if (to && to !== "/exceptions" && pathname.startsWith(`${to}/`)) {
    return true;
  }
  return childrenTo.some(
    (child) => pathname === child || (child !== "/exceptions" && pathname.startsWith(`${child}/`)),
  );
}

export function AppLayout() {
  const { pathname } = useLocation();
  const dispatch = useDispatch();
  const colorMode = useSelector((state: RootState) => state.ui.colorMode);
  const initiallyOpen = useMemo(() => {
    const open: Record<string, boolean> = {};
    for (const item of navItems) {
      if (item.children?.length) {
        open[item.label] = isPathActive(
          pathname,
          item.to,
          item.children.map((child) => child.to),
        );
      }
    }
    return open;
  }, [pathname]);
  const [openSections, setOpenSections] = useState<Record<string, boolean>>(initiallyOpen);

  useEffect(() => {
    setOpenSections((current) => ({ ...current, ...initiallyOpen }));
  }, [initiallyOpen]);

  return (
    <Box className="ufme-shell">
      <Box
        className="ufme-header"
        sx={{
          bgcolor: "transparent",
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          px: 2.5,
          zIndex: 10,
        }}
      >
        <Logo />

        <Box
          sx={{
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            width: 420,
            px: 1.25,
            py: 0.6,
            bgcolor: "var(--bg-muted)",
            border: "1px solid",
            borderColor: "var(--glass-border)",
            borderRadius: "8px",
            "&:focus-within": {
              bgcolor: "var(--glass-bg-strong)",
              borderColor: "primary.main",
              boxShadow: "0 0 0 3px var(--indigo-soft)",
            },
          }}
        >
          <Stack direction="row" alignItems="center" spacing={1} sx={{ flex: 1 }}>
            <SearchIcon sx={{ fontSize: 16, color: "var(--text-muted)" }} />
            <InputBase
              placeholder="Search entities, rules, transactions, cases..."
              sx={{ fontSize: 13, width: "100%", color: "text.secondary" }}
            />
          </Stack>
          <Box
            sx={{
              fontFamily: "var(--font-mono)",
              fontSize: 10.5,
              border: "1px solid var(--border-strong)",
              px: 0.6,
              borderRadius: "4px",
              color: "var(--text-secondary)",
            }}
          >
            ⌘K
          </Box>
        </Box>

        <Stack direction="row" alignItems="center" spacing={2} sx={{ fontSize: 13 }}>
          <Stack
            direction="row"
            alignItems="center"
            spacing={0.75}
            sx={{
              bgcolor: "var(--indigo-soft)",
              border: "1px solid color-mix(in srgb, var(--brand-indigo) 30%, transparent)",
              color: "var(--brand-indigo)",
              px: 1.1,
              py: 0.4,
              borderRadius: "6px",
              fontSize: 11,
              fontWeight: 500,
              fontFamily: "var(--font-mono)",
            }}
          >
            <Box className="status-dot" />
            ENGINE · LIVE
          </Stack>
          <Typography sx={{ fontFamily: "var(--font-mono)", fontSize: 11.5, color: "text.secondary" }}>
            PERIOD <Box component="span" sx={{ color: "text.primary" }}>Q3-2026</Box>
          </Typography>
          <IconButton size="small" onClick={() => dispatch(toggleColorMode())} aria-label="Toggle color mode">
            {colorMode === "dark" ? <LightModeOutlinedIcon fontSize="small" /> : <DarkModeOutlinedIcon fontSize="small" />}
          </IconButton>
          <Badge badgeContent={8} color="warning">
            <NotificationsNoneOutlinedIcon sx={{ color: "text.secondary" }} />
          </Badge>
          <ActingAs />
        </Stack>
      </Box>

      <Box
        className="ufme-nav"
        sx={{
          bgcolor: "transparent",
          py: 2,
          overflowY: "auto",
        }}
      >
        {navItems.map((item) => {
          const Icon = item.icon;
          const childPaths = item.children?.map((child) => child.to) ?? [];
          const sectionActive = isPathActive(pathname, item.to, childPaths);
          const expanded = Boolean(openSections[item.label]);

          if (!item.children) {
            return (
              <NavRow
                key={item.label}
                to={item.to!}
                label={item.label}
                icon={<Icon sx={{ fontSize: 16 }} />}
                active={sectionActive}
              />
            );
          }

          return (
            <Box key={item.label}>
              <NavRow
                label={item.label}
                icon={<Icon sx={{ fontSize: 16 }} />}
                active={sectionActive && !item.children.some((child) => pathname === child.to)}
                badge={item.badge}
                expanded={expanded}
                onClick={() => setOpenSections((current) => ({ ...current, [item.label]: !expanded }))}
              />
              <Collapse in={expanded} timeout={550} unmountOnExit>
                <Box sx={{ position: "relative", ml: 3.4, my: 0.25, borderLeft: "1px solid var(--border-strong)" }}>
                  {item.children.map((child) => (
                    <NavLink key={child.to} to={child.to} style={{ textDecoration: "none" }}>
                      {({ isActive }) => (
                        <Box
                          sx={{
                            position: "relative",
                            mr: 1.25,
                            px: 1.5,
                            py: 0.6,
                            fontSize: 12.5,
                            borderRadius: "6px",
                            color: isActive ? "text.primary" : "text.secondary",
                            fontWeight: isActive ? 550 : 450,
                            bgcolor: isActive ? "var(--bg-muted)" : "transparent",
                            "&:hover": { color: "text.primary" },
                            "&::before": isActive
                              ? {
                                  content: '""',
                                  position: "absolute",
                                  left: -1,
                                  top: 6,
                                  bottom: 6,
                                  width: 2,
                                  bgcolor: "var(--brand-indigo)",
                                  borderRadius: 2,
                                }
                              : undefined,
                          }}
                        >
                          {child.label}
                        </Box>
                      )}
                    </NavLink>
                  ))}
                </Box>
              </Collapse>
            </Box>
          );
        })}
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

type NavRowProps = {
  label: string;
  icon: ReactNode;
  active: boolean;
  to?: string;
  badge?: number;
  expanded?: boolean;
  onClick?: () => void;
};

function NavRow({ label, icon, active, to, badge, expanded, onClick }: NavRowProps) {
  const content = (
    <Stack
      direction="row"
      alignItems="center"
      justifyContent="space-between"
      onClick={onClick}
      sx={{
        mx: 1.25,
        my: 0.15,
        px: 1.25,
        py: 0.8,
        cursor: "pointer",
        fontSize: 13,
        borderRadius: "7px",
        fontWeight: active ? 550 : 450,
        color: active ? "text.primary" : "text.secondary",
        bgcolor: active ? "var(--bg-muted)" : "transparent",
        boxShadow: active ? "inset 0 0 0 1px var(--border-subtle)" : "none",
        "& svg": { color: active ? "var(--brand-indigo)" : "inherit" },
        transition: "background-color 0.5s cubic-bezier(0.22, 1, 0.36, 1), color 0.5s cubic-bezier(0.22, 1, 0.36, 1), border-color 0.5s cubic-bezier(0.22, 1, 0.36, 1)",
        "&:hover": { color: "text.primary", bgcolor: "var(--bg-muted)" },
      }}
    >
      <Stack direction="row" alignItems="center" spacing={1.25}>
        {icon}
        <span>{label}</span>
      </Stack>
      {badge ? (
        <Box
          sx={{
            fontSize: 10,
            fontWeight: 700,
            px: 0.75,
            py: 0.2,
            borderRadius: "5px",
            fontFamily: "var(--font-mono)",
            bgcolor: "var(--amber-soft)",
            color: "var(--brand-amber)",
          }}
        >
          {badge}
        </Box>
      ) : to ? null : (
        <ExpandMore sx={{ fontSize: 14, transform: expanded ? "rotate(180deg)" : "none", transition: "transform 0.5s cubic-bezier(0.22, 1, 0.36, 1)" }} />
      )}
    </Stack>
  );

  if (to) {
    return (
      <NavLink to={to} style={{ textDecoration: "none" }}>
        {content}
      </NavLink>
    );
  }
  return content;
}
