import { alpha, createTheme, type PaletteMode } from "@mui/material/styles";

/** "Precision" design system. Values mirror the CSS tokens in index.css so MUI and raw CSS agree. */
const tokens = {
  dark: {
    bg: "#07090d", surface: "#0c0f15", muted: "#11151d", border: "#1a1f29", borderStrong: "#272e3b",
    text: "#e9edf3", text2: "#8b94a5", text3: "#5a6373",
    primary: "#2ee6c0", onPrimary: "#04120e", secondary: "#8b9bff",
    success: "#4ade80", warning: "#f5b544", error: "#ff5d6c",
  },
  light: {
    bg: "#f5f6f8", surface: "#ffffff", muted: "#eef0f3", border: "#e3e6eb", borderStrong: "#cdd2da",
    text: "#0a0d12", text2: "#4a5260", text3: "#8a92a0",
    primary: "#0b9a82", onPrimary: "#ffffff", secondary: "#4c5bd4",
    success: "#12a150", warning: "#c27c0e", error: "#d93a4a",
  },
};

const sans = '"Instrument Sans", "Inter", system-ui, sans-serif';
export const display = '"Instrument Serif", Georgia, serif';
export const mono = '"JetBrains Mono", ui-monospace, "SFMono-Regular", monospace';
const ease = "cubic-bezier(0.16, 1, 0.3, 1)";

export function createAppTheme(mode: PaletteMode) {
  const t = tokens[mode];
  const isDark = mode === "dark";

  return createTheme({
    palette: {
      mode,
      primary: { main: t.primary, contrastText: t.onPrimary },
      secondary: { main: t.secondary },
      background: { default: t.bg, paper: t.surface },
      text: { primary: t.text, secondary: t.text2, disabled: t.text3 },
      success: { main: t.success },
      warning: { main: t.warning },
      error: { main: t.error },
      info: { main: t.secondary },
      divider: t.border,
      action: { hover: alpha(t.text, 0.04), selected: alpha(t.primary, 0.1) },
    },
    typography: {
      fontFamily: sans,
      fontSize: 13,
      h4: { fontFamily: display, fontWeight: 400, fontSize: 30, letterSpacing: "-0.01em", lineHeight: 1.15 },
      h5: { fontWeight: 600, letterSpacing: "-0.03em" },
      h6: { fontWeight: 600, fontSize: 13, letterSpacing: "-0.01em" },
      subtitle2: { fontWeight: 600 },
      body2: { fontSize: 13, lineHeight: 1.55 },
      caption: { color: t.text2 },
      overline: { fontFamily: mono, fontSize: 10.5, letterSpacing: "0.08em", fontWeight: 500, color: t.text3 },
      button: { textTransform: "none", fontWeight: 550, letterSpacing: "-0.005em" },
    },
    shape: { borderRadius: 8 },
    transitions: { easing: { easeInOut: ease, easeOut: ease, easeIn: "cubic-bezier(0.4, 0, 1, 1)", sharp: "cubic-bezier(0.4, 0, 0.6, 1)" } },
    components: {
      MuiCssBaseline: { styleOverrides: { body: { backgroundColor: "transparent" } } },
      MuiPaper: {
        defaultProps: { elevation: 0 },
        styleOverrides: { root: { backgroundImage: "none", backgroundColor: t.surface, border: `1px solid ${t.border}` } },
      },
      MuiBackdrop: { styleOverrides: { root: { backgroundColor: alpha(isDark ? "#000" : "#0a0d12", isDark ? 0.6 : 0.3), backdropFilter: "blur(4px)" } } },
      MuiButton: {
        defaultProps: { disableElevation: true },
        styleOverrides: {
          root: { borderRadius: 7, paddingInline: 14, minHeight: 32 },
          containedPrimary: { boxShadow: `0 0 0 1px ${alpha(t.primary, 0.4)}, 0 6px 20px -6px ${alpha(t.primary, isDark ? 0.55 : 0.4)}`, "&:hover": { backgroundColor: t.primary, filter: "brightness(1.08)" } },
          outlined: { borderColor: t.borderStrong, color: t.text, "&:hover": { borderColor: t.text3, backgroundColor: alpha(t.text, 0.04) } },
          sizeSmall: { minHeight: 28, fontSize: 12, paddingInline: 10 },
        },
      },
      MuiIconButton: { styleOverrides: { root: { borderRadius: 7, color: t.text2, "&:hover": { color: t.text } } } },
      MuiChip: {
        styleOverrides: {
          root: { borderRadius: 6, fontWeight: 500, fontSize: 11.5, height: 24 },
          outlined: { borderColor: t.borderStrong },
        },
      },
      MuiOutlinedInput: {
        styleOverrides: {
          root: {
            borderRadius: 7, backgroundColor: t.muted,
            "& .MuiOutlinedInput-notchedOutline": { borderColor: t.border },
            "&:hover .MuiOutlinedInput-notchedOutline": { borderColor: t.borderStrong },
            "&.Mui-focused .MuiOutlinedInput-notchedOutline": { borderColor: t.primary, borderWidth: 1, boxShadow: `0 0 0 3px ${alpha(t.primary, 0.15)}` },
          },
        },
      },
      MuiTabs: { styleOverrides: { indicator: { height: 2, borderRadius: 2, backgroundColor: t.primary } } },
      MuiTab: { styleOverrides: { root: { textTransform: "none", fontWeight: 500, minHeight: 40, fontSize: 13, "&.Mui-selected": { color: t.text } } } },
      MuiTooltip: {
        styleOverrides: {
          tooltip: { backgroundColor: isDark ? "#1a1f29" : "#0a0d12", color: "#e9edf3", fontSize: 11.5, border: `1px solid ${isDark ? t.borderStrong : "transparent"}`, borderRadius: 6 },
        },
      },
      MuiLinearProgress: {
        styleOverrides: { root: { height: 4, borderRadius: 4, backgroundColor: t.muted }, bar: { borderRadius: 4 } },
      },
      MuiCollapse: { defaultProps: { timeout: 320 } },
      MuiDrawer: { defaultProps: { transitionDuration: { enter: 420, exit: 260 } }, styleOverrides: { paper: { backgroundColor: t.surface, borderLeft: `1px solid ${t.borderStrong}` } } },
      MuiDialog: { defaultProps: { transitionDuration: { enter: 320, exit: 200 } }, styleOverrides: { paper: { backgroundColor: t.surface, border: `1px solid ${t.borderStrong}`, boxShadow: isDark ? "0 24px 80px rgba(0,0,0,0.6)" : "0 24px 80px rgba(10,13,18,0.14)" } } },
      MuiTableCell: {
        styleOverrides: {
          root: { fontSize: 12.5, paddingTop: 10, paddingBottom: 10, borderColor: t.border },
          head: { fontFamily: mono, fontWeight: 500, fontSize: 10.5, letterSpacing: "0.06em", textTransform: "uppercase", color: t.text3, backgroundColor: t.surface },
        },
      },
      MuiTableRow: { styleOverrides: { root: { "&.MuiTableRow-hover:hover": { backgroundColor: alpha(t.primary, isDark ? 0.04 : 0.035) } } } },
      MuiAlert: { styleOverrides: { root: { borderRadius: 8, border: "1px solid", fontSize: 13 } } },
      MuiSnackbarContent: { styleOverrides: { root: { backgroundColor: isDark ? "#1a1f29" : "#0a0d12", color: "#e9edf3", border: `1px solid ${t.borderStrong}` } } },
    },
  });
}
