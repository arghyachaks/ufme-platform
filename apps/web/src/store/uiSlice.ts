import { createSlice } from "@reduxjs/toolkit";

type UiState = {
  title: string;
};

const initialState: UiState = {
  title: "Universal Financial Matching Engine",
};

const uiSlice = createSlice({
  name: "ui",
  initialState,
  reducers: {},
});

export const uiReducer = uiSlice.reducer;
