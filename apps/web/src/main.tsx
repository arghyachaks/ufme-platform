import { useMemo } from "react";
import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { Provider, useSelector } from "react-redux";
import { CssBaseline, ThemeProvider } from "@mui/material";
import App from "./app/App";
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

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <Provider store={store}>
      <ThemedApp />
    </Provider>
  </StrictMode>,
);
