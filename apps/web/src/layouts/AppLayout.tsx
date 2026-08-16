import { NavLink, Outlet } from "react-router-dom";
import { Box, Drawer, List, ListItemButton, ListItemText, Toolbar, Typography } from "@mui/material";

const drawerWidth = 240;

const navItems = [
  { to: "/dashboard", label: "Dashboard" },
  { to: "/matches", label: "Match workbench" },
  { to: "/rules", label: "Rule designer" },
  { to: "/policies", label: "Policy manager" },
  { to: "/analytics", label: "Analytics" },
  { to: "/copilot", label: "AI Copilot" },
  { to: "/admin", label: "Admin console" },
];

export function AppLayout() {
  return (
    <Box sx={{ display: "flex", minHeight: "100vh" }}>
      <Drawer
        variant="permanent"
        sx={{
          width: drawerWidth,
          flexShrink: 0,
          "& .MuiDrawer-paper": { width: drawerWidth, boxSizing: "border-box" },
        }}
      >
        <Toolbar>
          <Typography variant="h6">UFME</Typography>
        </Toolbar>
        <List>
          {navItems.map((item) => (
            <ListItemButton key={item.to} component={NavLink} to={item.to}>
              <ListItemText primary={item.label} />
            </ListItemButton>
          ))}
        </List>
      </Drawer>
      <Box component="main" sx={{ flexGrow: 1, p: 3 }}>
        <Outlet />
      </Box>
    </Box>
  );
}
