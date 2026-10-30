import { useMemo } from "react";
import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { Provider, useSelector } from "react-redux";
import { CssBaseline, ThemeProvider } from "@mui/material";
import App from "./app/App";
import { initAuth } from "./auth/oidc";
import { store, type RootState } from "./store";
import { createAppTheme } from "./theme";
import "./index.css";

function ThemedApp() {
  const colorMode = useSelector((state: RootState) => state.ui.colorMode);
  const theme = useMemo(() => createAppTheme(colorMode), [colorMode]);

  return (
    <ThemeProvider theme={theme}>
      <CssBaseline />
      <div className="ufme-root" data-theme={colorMode}>
        <App />
      </div>
    </ThemeProvider>
  );
}

const root = createRoot(document.getElementById("root")!);

// Finish or start OIDC sign-in before anything calls the API (no-op in dev mode).
initAuth()
  .then(() =>
    root.render(
      <StrictMode>
        <Provider store={store}>
          <ThemedApp />
        </Provider>
      </StrictMode>,
    ),
  )
  .catch((err: unknown) =>
    root.render(
      <div style={{ fontFamily: "system-ui, sans-serif", padding: 32, maxWidth: 520 }}>
        <h2 style={{ fontWeight: 600 }}>Sign-in didn't complete</h2>
        <p>{err instanceof Error ? err.message : String(err)}</p>
        <button onClick={() => window.location.assign("/")}>Try again</button>
      </div>,
    ),
  );
