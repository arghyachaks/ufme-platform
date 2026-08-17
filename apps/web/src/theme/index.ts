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
    components: {
      MuiCssBaseline: {
        styleOverrides: {
          body: {
            backgroundColor: isDark ? "#0b1220" : "#f8fafc",
          },
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
