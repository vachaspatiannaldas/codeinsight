import api from "./api";

export const submitReview = async (diff) => {

  const response = await api.post(
    "/review/",
    {
      repository_name: "demo-repo",
      pr_number: 1,
      diff,
    }
  );

  return response.data;
};

export const fetchReview = async (reviewId) => {

  const response = await api.get(
    `/review/${reviewId}/`
  );

  return response.data;
};