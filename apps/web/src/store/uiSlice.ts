import { createSlice } from "@reduxjs/toolkit";

type ColorMode = "light" | "dark";

type UiState = {
  colorMode: ColorMode;
};

const initialState: UiState = {
  colorMode: "light",
};

const uiSlice = createSlice({
  name: "ui",
  initialState,
  reducers: {
    toggleColorMode(state) {
      state.colorMode = state.colorMode === "light" ? "dark" : "light";
    },
  },
});

export const { toggleColorMode } = uiSlice.actions;
export const uiReducer = uiSlice.reducer;
