"use client";

import { useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import type { QuerySummary, QueryListResponse, QueryResponse, CandidateResult } from "@/types/api";
import LoadingSpinner from "@/components/LoadingSpinner";
import ErrorAlert from "@/components/ErrorAlert";
import QueryTable from "@/components/history/QueryTable";
import QueryDiff from "@/components/history/QueryDiff";

const PER_PAGE = 20;

export default function QueryHistoryPage() {
  const router = useRouter();
  const [queries, setQueries] = useState<QuerySummary[]>([]);
  const [totalPages, setTotalPages] = useState(1);
  const [currentPage, setCurrentPage] = useState(1);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Diff state
  const [diffOldResults, setDiffOldResults] = useState<CandidateResult[] | null>(null);
  const [diffNewResults, setDiffNewResults] = useState<CandidateResult[] | null>(null);
  const [diffLoading, setDiffLoading] = useState(false);

  const fetchQueries = useCallback(async (page: number) => {
    setLoading(true);
    setError(null);
    try {
      const response = await fetch(
        `/api/queries?page=${page}&per_page=${PER_PAGE}`
      );
      if (!response.ok) {
        throw new Error(`Failed to load query history: ${response.status}`);
      }
      const data: QueryListResponse = await response.json();
      setQueries(data.queries);
      setTotalPages(Math.max(1, Math.ceil(data.total / PER_PAGE)));
      setCurrentPage(page);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load query history.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchQueries(1); // eslint-disable-line react-hooks/set-state-in-effect
  }, [fetchQueries]);

  const handleRerun = async (query: QuerySummary) => {
    setDiffLoading(true);
    setDiffOldResults(null);
    setDiffNewResults(null);
    try {
      // Fetch old results
      const oldResponse = await fetch(`/api/queries/${query.id}`);
      if (!oldResponse.ok) throw new Error("Failed to fetch old results");
      const oldData: QueryResponse = await oldResponse.json();

      // Re-run the query
      const rerunResponse = await fetch("/api/queries", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          task_description: query.task_description,
          population: query.population,
          k: query.k,
        }),
      });
      if (!rerunResponse.ok) throw new Error("Failed to re-run query");
      const rerunData = await rerunResponse.json();
      const newId = rerunData.id;

      // Poll for new results (simple retry)
      let newData: QueryResponse | null = null;
      for (let i = 0; i < 30; i++) {
        await new Promise((r) => setTimeout(r, 1000));
        const newResponse = await fetch(`/api/queries/${newId}`);
        if (newResponse.ok) {
          const data: QueryResponse = await newResponse.json();
          if (data.candidates && data.candidates.length > 0) {
            newData = data;
            break;
          }
        }
      }

      if (newData) {
        setDiffOldResults(oldData.candidates);
        setDiffNewResults(newData.candidates);
      } else {
        // If polling timed out, just navigate to new results
        router.push(`/results/${newId}`);
      }
    } catch {
      // On error, just refresh
    } finally {
      setDiffLoading(false);
      fetchQueries(currentPage);
    }
  };

  const closeDiff = () => {
    setDiffOldResults(null);
    setDiffNewResults(null);
  };

  return (
    <div>
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Query History</h1>
        <p className="mt-2 text-sm text-gray-600">
          View past queries and their results, newest first.
        </p>
      </div>

      {/* Diff loading indicator */}
      {diffLoading && (
        <div className="mb-6 bg-blue-50 border border-blue-200 rounded-lg p-4">
          <div className="flex items-center gap-2">
            <svg className="animate-spin h-4 w-4 text-blue-600" fill="none" viewBox="0 0 24 24">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
            </svg>
            <span className="text-sm text-blue-800">Re-running query and comparing results...</span>
          </div>
        </div>
      )}

      {/* Diff view */}
      {diffOldResults && diffNewResults && (
        <div className="mb-6 bg-white border border-gray-200 rounded-lg overflow-hidden">
          <div className="flex items-center justify-between px-6 py-3 bg-gray-50 border-b border-gray-200">
            <h2 className="text-sm font-semibold text-gray-900">Ranking Comparison</h2>
            <button
              onClick={closeDiff}
              className="text-xs text-gray-500 hover:text-gray-700"
            >
              Close
            </button>
          </div>
          <QueryDiff oldResults={diffOldResults} newResults={diffNewResults} />
        </div>
      )}

      {loading ? (
        <LoadingSpinner message="Loading query history..." />
      ) : error ? (
        <ErrorAlert message={error} onRetry={() => fetchQueries(currentPage)} />
      ) : (
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 overflow-hidden">
          <QueryTable queries={queries} onRerun={handleRerun} />

          {totalPages > 1 && (
            <div className="flex items-center justify-between px-6 py-3 bg-gray-50 border-t border-gray-200">
              <button
                onClick={() => fetchQueries(currentPage - 1)}
                disabled={currentPage <= 1}
                className="px-3 py-1 rounded-md border border-gray-300 text-sm text-gray-700 hover:bg-white disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              >
                Previous
              </button>
              <span className="text-sm text-gray-600">
                Page {currentPage} of {totalPages}
              </span>
              <button
                onClick={() => fetchQueries(currentPage + 1)}
                disabled={currentPage >= totalPages}
                className="px-3 py-1 rounded-md border border-gray-300 text-sm text-gray-700 hover:bg-white disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              >
                Next
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
