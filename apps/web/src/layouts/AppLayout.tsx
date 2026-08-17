import type { ReactNode } from "react";
import { useEffect, useMemo, useState } from "react";
import { NavLink, Outlet, useLocation } from "react-router-dom";
import { Avatar, Badge, Box, Collapse, IconButton, InputBase, Stack, Typography } from "@mui/material";
import DarkModeOutlinedIcon from "@mui/icons-material/DarkModeOutlined";
import ExpandMore from "@mui/icons-material/ExpandMore";
import LightModeOutlinedIcon from "@mui/icons-material/LightModeOutlined";
import NotificationsNoneOutlinedIcon from "@mui/icons-material/NotificationsNoneOutlined";
import SearchIcon from "@mui/icons-material/Search";
import { useDispatch, useSelector } from "react-redux";
import { navItems } from "../navigation/navConfig";
import { ActivityTicker } from "../components/shell/ActivityTicker";
import { CopilotDock } from "../components/shell/CopilotDock";
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
          bgcolor: "background.paper",
          borderBottom: "1px solid",
          borderColor: "divider",
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          px: 2.5,
          zIndex: 10,
        }}
      >
        <Stack direction="row" alignItems="center" spacing={1.25}>
          <Box
            sx={{
              width: 28,
              height: 28,
              borderRadius: "6px",
              background: "linear-gradient(135deg, #4f46e5, #0284c7)",
              color: "#fff",
              fontWeight: 800,
              fontSize: 14,
              display: "grid",
              placeItems: "center",
              boxShadow: "0 2px 8px rgba(79,70,229,0.3)",
            }}
          >
            U
          </Box>
          <Typography sx={{ fontWeight: 700, fontSize: 18, letterSpacing: "-0.02em", color: "text.primary" }}>
            UFME
          </Typography>
          <Typography sx={{ fontSize: 11, fontWeight: 500, color: "#94a3b8" }}>v4.2 Enterprise</Typography>
        </Stack>

        <Box
          sx={{
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            width: 380,
            px: 1.75,
            py: 0.75,
            bgcolor: "var(--bg-muted)",
            border: "1px solid",
            borderColor: "divider",
            borderRadius: "6px",
            "&:focus-within": {
              bgcolor: "background.paper",
              borderColor: "secondary.main",
              boxShadow: "0 0 0 3px rgba(2,132,199,0.1)",
            },
          }}
        >
          <Stack direction="row" alignItems="center" spacing={1} sx={{ flex: 1 }}>
            <SearchIcon sx={{ fontSize: 16, color: "#94a3b8" }} />
            <InputBase
              placeholder="Search entities, rules, transactions, cases..."
              sx={{ fontSize: 13, width: "100%", color: "text.secondary" }}
            />
          </Stack>
          <Box
            sx={{
              fontFamily: '"IBM Plex Sans", sans-serif',
              fontSize: 11,
              bgcolor: "#e2e8f0",
              px: 0.75,
              borderRadius: "4px",
              color: "#475569",
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
              bgcolor: "#ecfdf5",
              border: "1px solid rgba(5,150,105,0.3)",
              color: "#059669",
              px: 1.25,
              py: 0.5,
              borderRadius: 10,
              fontSize: 11,
              fontWeight: 600,
            }}
          >
            <Box className="status-dot" />
            Autonomous Matching Engine: Active
          </Stack>
          <Typography sx={{ fontFamily: '"IBM Plex Sans", sans-serif', fontSize: 13, color: "text.secondary" }}>
            Period: <Box component="strong" sx={{ color: "text.primary" }}>Q3-2026</Box>
          </Typography>
          <IconButton size="small" onClick={() => dispatch(toggleColorMode())} aria-label="Toggle color mode">
            {colorMode === "dark" ? <LightModeOutlinedIcon fontSize="small" /> : <DarkModeOutlinedIcon fontSize="small" />}
          </IconButton>
          <Badge badgeContent={8} color="warning">
            <NotificationsNoneOutlinedIcon sx={{ color: "text.secondary" }} />
          </Badge>
          <Stack direction="row" alignItems="center" spacing={1}>
            <Avatar sx={{ width: 28, height: 28, bgcolor: "#4f46e5", fontSize: 12, fontWeight: 700 }}>FC</Avatar>
            <Typography sx={{ fontWeight: 600, fontSize: 13 }}>FinController_Global</Typography>
          </Stack>
        </Stack>
      </Box>

      <Box
        className="ufme-nav"
        sx={{
          bgcolor: "background.paper",
          borderRight: "1px solid",
          borderColor: "divider",
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
                <Box sx={{ bgcolor: "var(--bg-muted)", borderTop: 1, borderBottom: 1, borderColor: "divider" }}>
                  {item.children.map((child) => (
                    <NavLink key={child.to} to={child.to} style={{ textDecoration: "none" }}>
                      {({ isActive }) => (
                        <Box
                          sx={{
                            position: "relative",
                            px: 2.5,
                            py: 0.75,
                            pl: 4.75,
                            fontSize: 12,
                            color: isActive ? "secondary.main" : "text.secondary",
                            fontWeight: isActive ? 600 : 500,
                            bgcolor: isActive ? "var(--blue-soft)" : "transparent",
                            "&:hover": { color: "secondary.main", bgcolor: "var(--blue-soft)", pl: 5.25 },
                            "&::before": isActive
                              ? {
                                  content: '""',
                                  position: "absolute",
                                  left: 28,
                                  top: "50%",
                                  transform: "translateY(-50%)",
                                  width: 4,
                                  height: 4,
                                  bgcolor: "#0284c7",
                                  borderRadius: "50%",
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
        px: 2.5,
        py: 1,
        cursor: "pointer",
        fontSize: 13,
        fontWeight: active ? 600 : 500,
        color: active ? "primary.main" : "text.secondary",
        bgcolor: active ? "var(--indigo-soft)" : "transparent",
        borderRight: active ? "3px solid #4f46e5" : "3px solid transparent",
        transition: "background-color 0.5s cubic-bezier(0.22, 1, 0.36, 1), color 0.5s cubic-bezier(0.22, 1, 0.36, 1), border-color 0.5s cubic-bezier(0.22, 1, 0.36, 1)",
        "&:hover": { color: "primary.main", bgcolor: "var(--indigo-soft)" },
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
            borderRadius: 10,
            bgcolor: "#fffbeb",
            color: "#d97706",
            border: "1px solid rgba(217,119,6,0.3)",
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
