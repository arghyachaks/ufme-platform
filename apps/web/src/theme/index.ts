import { createTheme, type PaletteMode } from "@mui/material/styles";

export function createAppTheme(mode: PaletteMode) {
  const isDark = mode === "dark";

  return createTheme({
    palette: {
      mode,
      primary: { main: "#4f46e5", contrastText: "#ffffff" },
      secondary: { main: "#0284c7" },
      background: {
        default: isDark ? "#0b1220" : "#f8fafc",
        paper: isDark ? "#111827" : "#ffffff",
      },
      text: {
        primary: isDark ? "#e5eef7" : "#0f172a",
        secondary: isDark ? "#94a3b8" : "#475569",
      },
      success: { main: "#059669" },
      warning: { main: "#d97706" },
      error: { main: "#dc2626" },
      divider: isDark ? "#1f2a3d" : "#e2e8f0",
    },
    typography: {
      fontFamily: "Inter, system-ui, sans-serif",
      h4: { fontWeight: 700, letterSpacing: "-0.02em" },
      h6: { fontWeight: 700, fontSize: 14 },
      subtitle2: { fontWeight: 700 },
      button: { textTransform: "none", fontWeight: 600 },
    },
    shape: { borderRadius: 8 },
    transitions: {
      duration: {
        shortest: 280,
        shorter: 400,
        short: 500,
        standard: 600,
        complex: 800,
        enteringScreen: 700,
        leavingScreen: 550,
      },
      easing: {
        easeInOut: "cubic-bezier(0.4, 0, 0.2, 1)",
        easeOut: "cubic-bezier(0.22, 1, 0.36, 1)",
        easeIn: "cubic-bezier(0.4, 0, 1, 1)",
        sharp: "cubic-bezier(0.4, 0, 0.6, 1)",
      },
    },
    components: {
      MuiCssBaseline: {
        styleOverrides: {
          body: {
            backgroundColor: isDark ? "#0b1220" : "#f8fafc",
          },
        },
      },
      MuiButton: {
        styleOverrides: {
          root: {
            transition: "background-color 0.5s cubic-bezier(0.22, 1, 0.36, 1), color 0.5s cubic-bezier(0.22, 1, 0.36, 1), border-color 0.5s cubic-bezier(0.22, 1, 0.36, 1), box-shadow 0.55s cubic-bezier(0.22, 1, 0.36, 1), transform 0.55s cubic-bezier(0.22, 1, 0.36, 1)",
          },
        },
      },
      MuiCollapse: {
        defaultProps: {
          timeout: 550,
        },
      },
      MuiTableCell: {
        styleOverrides: {
          root: {
            fontSize: 12,
            paddingTop: 10,
            paddingBottom: 10,
          },
          head: { fontWeight: 600 },
        },
      },
    },
  });
}
