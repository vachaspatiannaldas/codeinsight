import { configureStore } from "@reduxjs/toolkit";

import reviewReducer from "./reviewSlice";

export const store = configureStore({
  reducer: {
    review: reviewReducer,
  },
});