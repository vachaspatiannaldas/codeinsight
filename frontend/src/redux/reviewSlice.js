import { createSlice } from "@reduxjs/toolkit";

const initialState = {
  loading: false,
  reviewId: null,
  reviewData: null,
  error: null,
};

const reviewSlice = createSlice({
  name: "review",

  initialState,

  reducers: {

    startLoading: (state) => {
      state.loading = true;
      state.error = null;
    },

    setReviewId: (state, action) => {
      state.reviewId = action.payload;
    },

    setReviewData: (state, action) => {
      state.reviewData = action.payload;
      state.loading = false;
    },

    setError: (state, action) => {
      state.error = action.payload;
      state.loading = false;
    },

    resetReview: (state) => {
      state.loading = false;
      state.reviewId = null;
      state.reviewData = null;
      state.error = null;
    },
  },
});

export const {
  startLoading,
  setReviewId,
  setReviewData,
  setError,
  resetReview,
} = reviewSlice.actions;

export default reviewSlice.reducer;