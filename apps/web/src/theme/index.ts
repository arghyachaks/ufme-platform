import { alpha, createTheme, type PaletteMode } from "@mui/material/styles";

/** ufme editorial system (Jasper-style structure, Campfire green). Mirrors the CSS tokens in index.css. */
const tokens = {
  dark: {
    bg: "#00052e", surface: "#050b3d", muted: "#0c1350", border: "#1b2263", borderStrong: "#c9cbe0",
    text: "#f6f6f8", text2: "#c3c5da", text3: "#9a9dbb",
    primary: "#b3ed97", onPrimary: "#00063d", secondary: "#9fb4ff",
    success: "#b3ed97", warning: "#ffe27a", error: "#ff9a86",
  },
  light: {
    bg: "#ffffff", surface: "#ffffff", muted: "#f2f2f3", border: "#e2e3ea", borderStrong: "#00063d",
    text: "#00063d", text2: "#3d4266", text3: "#62668a",
    primary: "#0a4733", onPrimary: "#ffffff", secondary: "#0011a7",
    success: "#0a4733", warning: "#7a5200", error: "#c42d1a",
  },
};

const sans = '"Geist", "Inter", Arial, sans-serif';
export const display = '"Newsreader", Georgia, serif';
export const mono = '"Geist Mono", ui-monospace, "SFMono-Regular", monospace';
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
      fontSize: 14,
      h4: { fontFamily: display, fontWeight: 400, fontSize: 44, letterSpacing: "-0.03em", lineHeight: 1.04 },
      h5: { fontFamily: display, fontWeight: 400, fontSize: 28, letterSpacing: "-0.02em" },
      h6: { fontFamily: display, fontWeight: 400, fontSize: 21, letterSpacing: "-0.01em", lineHeight: 1.15 },
      subtitle2: { fontWeight: 600 },
      body2: { fontSize: 14, lineHeight: 1.55 },
      caption: { color: t.text2 },
      overline: { fontFamily: mono, fontSize: 11.5, letterSpacing: "0.04em", fontWeight: 400, color: t.text2 },
      button: { textTransform: "none", fontWeight: 500, letterSpacing: "-0.01em" },
    },
    shape: { borderRadius: 4 },
    transitions: { easing: { easeInOut: ease, easeOut: ease, easeIn: "cubic-bezier(0.4, 0, 1, 1)", sharp: "cubic-bezier(0.4, 0, 0.6, 1)" } },
    components: {
      MuiCssBaseline: { styleOverrides: { body: { backgroundColor: "transparent" } } },
      MuiPaper: {
        defaultProps: { elevation: 0 },
        styleOverrides: { root: { backgroundImage: "none", backgroundColor: t.surface, border: `1px solid ${t.borderStrong}`, borderRadius: 2 } },
      },
      MuiBackdrop: { styleOverrides: { root: { backgroundColor: alpha("#00063d", isDark ? 0.6 : 0.35) } } },
      MuiButton: {
        defaultProps: { disableElevation: true },
        styleOverrides: {
          root: { borderRadius: 4, paddingInline: 18, minHeight: 40, fontSize: 14.5 },
          containedPrimary: { boxShadow: "none", "&:hover": { backgroundColor: isDark ? "#d2ffc1" : "#142d25", boxShadow: "none" } },
          outlined: { borderColor: t.borderStrong, color: t.text, "&:hover": { borderColor: t.borderStrong, backgroundColor: t.text, color: t.surface } },
          text: { color: t.text, "&:hover": { backgroundColor: t.muted } },
          sizeSmall: { minHeight: 32, fontSize: 13, paddingInline: 12 },
        },
      },
      MuiIconButton: { styleOverrides: { root: { borderRadius: 4, color: t.text2, "&:hover": { color: t.text, backgroundColor: t.muted } } } },
      MuiChip: {
        styleOverrides: {
          root: { borderRadius: 9999, fontWeight: 500, fontSize: 12, height: 26 },
          outlined: { borderColor: t.borderStrong },
        },
      },
      MuiOutlinedInput: {
        styleOverrides: {
          root: {
            borderRadius: 4, backgroundColor: t.surface,
            "& .MuiOutlinedInput-notchedOutline": { borderColor: alpha(t.borderStrong, 0.45) },
            "&:hover .MuiOutlinedInput-notchedOutline": { borderColor: t.borderStrong },
            "&.Mui-focused .MuiOutlinedInput-notchedOutline": { borderColor: t.primary, borderWidth: 2 },
          },
        },
      },
      MuiTabs: { styleOverrides: { root: { borderBottom: `1px solid ${t.borderStrong}` }, indicator: { height: 3, borderRadius: 0, backgroundColor: t.primary } } },
      MuiTab: { styleOverrides: { root: { textTransform: "none", fontWeight: 500, minHeight: 44, fontSize: 14.5, color: t.text2, "&.Mui-selected": { color: t.text } } } },
      MuiTooltip: {
        styleOverrides: {
          tooltip: { backgroundColor: isDark ? "#f6f6f8" : "#00063d", color: isDark ? "#00063d" : "#ffffff", fontSize: 12, borderRadius: 2 },
        },
      },
      MuiLinearProgress: {
        styleOverrides: { root: { height: 6, borderRadius: 0, backgroundColor: t.muted }, bar: { borderRadius: 0 } },
      },
      MuiCollapse: { defaultProps: { timeout: 320 } },
      MuiDrawer: { defaultProps: { transitionDuration: { enter: 420, exit: 260 } }, styleOverrides: { paper: { backgroundColor: t.surface, borderLeft: `1px solid ${t.borderStrong}` } } },
      MuiDialog: { defaultProps: { transitionDuration: { enter: 320, exit: 200 } }, styleOverrides: { paper: { backgroundColor: t.surface, border: `1px solid ${t.borderStrong}`, borderRadius: 2, boxShadow: "none" } } },
      MuiMenu: { styleOverrides: { paper: { border: `1px solid ${t.borderStrong}`, borderRadius: 2, boxShadow: "none", marginTop: 6 } } },
      MuiTableCell: {
        styleOverrides: {
          root: { fontSize: 14, paddingTop: 13, paddingBottom: 13, borderColor: t.border },
          head: { fontFamily: sans, fontWeight: 500, fontSize: 13, color: t.text, backgroundColor: t.surface, borderBottom: `1px solid ${t.borderStrong}` },
        },
      },
      MuiTableRow: { styleOverrides: { root: { "&.MuiTableRow-hover:hover": { backgroundColor: isDark ? alpha("#b3ed97", 0.08) : "#f2f2f3" }, "&.Mui-selected, &.Mui-selected:hover": { backgroundColor: isDark ? alpha("#b3ed97", 0.14) : "#e6ffd9" } } } },
      MuiAlert: { styleOverrides: { root: { borderRadius: 2, border: "1px solid", fontSize: 14 } } },
      MuiSnackbarContent: { styleOverrides: { root: { backgroundColor: isDark ? "#f6f6f8" : "#00063d", color: isDark ? "#00063d" : "#ffffff", borderRadius: 2, boxShadow: "none" } } },
    },
  });
}
