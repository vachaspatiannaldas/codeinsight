import { useState } from "react";
import { useDispatch, useSelector } from "react-redux";

import {
  startLoading,
  setReviewId,
  setReviewData,
  setError,
} from "./redux/reviewSlice";

import {
  submitReview,
  fetchReview,
} from "./services/reviewService";

import ReviewCard from "./components/ReviewCard";

export default function App() {

  const dispatch = useDispatch();

  const {
    loading,
    reviewData,
    error,
  } = useSelector(
    (state) => state.review
  );

  const [diff, setDiff] = useState("");

  const pollReviewResult = async (
    reviewId
  ) => {

    const interval = setInterval(
      async () => {

        try {

          const data = await fetchReview(
            reviewId
          );

          if (
            data.status === "completed"
          ) {

            dispatch(
              setReviewData(data)
            );

            clearInterval(interval);
          }

        } catch (err) {

          dispatch(
            setError(
              "Polling failed"
            )
          );

          clearInterval(interval);
        }

      },
      3000
    );
  };

  const handleAnalyze = async () => {

    if (!diff.trim()) return;

    try {

      dispatch(startLoading());

      const response =
        await submitReview(diff);

      dispatch(
        setReviewId(
          response.review_id
        )
      );

      pollReviewResult(
        response.review_id
      );

    } catch (err) {

      dispatch(
        setError(
          "Failed to analyze PR"
        )
      );
    }
  };

  return (
    <div className="min-h-screen bg-gray-100 p-10">

      <div className="max-w-5xl mx-auto">

        <h1 className="text-5xl font-bold mb-8">
          CodeInsight
        </h1>

        <p className="text-lg mb-5">
         A code quality analysis platform using AI
        </p>

        <textarea
          value={diff}
          onChange={(e) =>
            setDiff(e.target.value)
          }
          className="
            w-full
            h-64
            p-5
            rounded-xl
            border
            text-sm
            font-mono
            bg-white
          "
          placeholder="Paste Pull Request Diff or Source Code..."
        />

        <button
          onClick={handleAnalyze}
          disabled={loading}
          className="
            mt-5
            px-8
            py-4
            bg-black
            text-white
            rounded-xl
            font-semibold
          "
        >
          {
            loading
              ? "Analyzing..."
              : "Analyze with AI"
          }
        </button>

        {
          error && (
            <div className="
              mt-6
              bg-red-100
              text-red-700
              p-4
              rounded-xl
            ">
              {error}
            </div>
          )
        }

        {
          reviewData?.ai_response
            ?.issues && (

            <div className="mt-10">

              <h2 className="
                text-3xl
                font-bold
                mb-6
              ">
                Review Results
              </h2>

              {
                reviewData
                  .ai_response
                  .issues
                  .map(
                    (
                      issue,
                      index
                    ) => (
                      <ReviewCard
                        key={index}
                        issue={issue}
                      />
                    )
                  )
              }

            </div>
          )
        }

      </div>

    </div>
  );
}

