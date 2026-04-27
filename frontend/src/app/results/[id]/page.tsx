"use client";

import { useCallback, useEffect, useState } from "react";
import { useParams } from "next/navigation";
import type { QueryResponse } from "@/types/api";
import LoadingSpinner from "@/components/LoadingSpinner";
import ErrorAlert from "@/components/ErrorAlert";
import CandidateRow from "@/components/results/CandidateRow";
import FeedbackModal from "@/components/results/FeedbackModal";

export default function ResultsPage() {
  const params = useParams();
  const queryId = params.id as string;

  const [query, setQuery] = useState<QueryResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showFeedback, setShowFeedback] = useState(false);
  const [feedbackSubmitted, setFeedbackSubmitted] = useState(false);

  const fetchQuery = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await fetch(`/api/queries/${queryId}`);
      if (!response.ok) {
        throw new Error(`Failed to load query results: ${response.status}`);
      }
      const data: QueryResponse = await response.json();
      setQuery(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load results.");
    } finally {
      setLoading(false);
    }
  }, [queryId]);

  useEffect(() => {
    if (queryId) {
      fetchQuery(); // eslint-disable-line react-hooks/set-state-in-effect
    }
  }, [queryId, fetchQuery]);

  if (loading) return <LoadingSpinner message="Loading results..." />;
  if (error) return <ErrorAlert message={error} onRetry={fetchQuery} />;
  if (!query) return null;

  return (
    <div>
      {/* Query header */}
      <div className="mb-6">
        <div className="flex items-start justify-between">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">Query Results</h1>
            <p className="mt-2 text-sm text-gray-600 max-w-3xl">{query.task_description}</p>
            <div className="flex items-center space-x-4 mt-2 text-xs text-gray-500">
              {query.population && (
                <span className="inline-flex items-center rounded-full bg-gray-100 px-2 py-0.5 font-medium">
                  {query.population.replace("_", " ")}
                </span>
              )}
              <span>K = {query.k}</span>
              <span>{query.candidates.length} results</span>
              <span>{new Date(query.created_at).toLocaleString()}</span>
            </div>
          </div>

          {/* Submit Feedback button */}
          <div>
            {feedbackSubmitted ? (
              <span className="inline-flex items-center rounded-md bg-green-50 px-3 py-2 text-sm font-medium text-green-700">
                Feedback submitted
              </span>
            ) : (
              <button
                onClick={() => setShowFeedback(true)}
                className="px-4 py-2 rounded-md bg-white border border-gray-300 text-sm font-medium text-gray-700 hover:bg-gray-50 shadow-sm transition-colors"
              >
                Submit Feedback
              </button>
            )}
          </div>
        </div>
      </div>

      {/* Candidate list */}
      {query.candidates.length === 0 ? (
        <div className="text-center py-12">
          <p className="text-gray-500">No candidates found for this query.</p>
        </div>
      ) : (
        <div className="space-y-3">
          {query.candidates.map((candidate) => (
            <CandidateRow key={candidate.uuid} candidate={candidate} />
          ))}
        </div>
      )}

      {/* Feedback modal */}
      {showFeedback && (
        <FeedbackModal
          queryId={queryId}
          onClose={() => setShowFeedback(false)}
          onSuccess={() => {
            setShowFeedback(false);
            setFeedbackSubmitted(true);
          }}
        />
      )}
    </div>
  );
}
