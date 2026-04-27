"use client";

import { useCallback, useEffect, useState } from "react";
import type { QuerySummary, QueryListResponse } from "@/types/api";
import LoadingSpinner from "@/components/LoadingSpinner";
import ErrorAlert from "@/components/ErrorAlert";
import QueryTable from "@/components/history/QueryTable";

const PER_PAGE = 20;

export default function QueryHistoryPage() {
  const [queries, setQueries] = useState<QuerySummary[]>([]);
  const [totalPages, setTotalPages] = useState(1);
  const [currentPage, setCurrentPage] = useState(1);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

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

  return (
    <div>
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Query History</h1>
        <p className="mt-2 text-sm text-gray-600">
          View past queries and their results, newest first.
        </p>
      </div>

      {loading ? (
        <LoadingSpinner message="Loading query history..." />
      ) : error ? (
        <ErrorAlert message={error} onRetry={() => fetchQueries(currentPage)} />
      ) : (
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 overflow-hidden">
          <QueryTable queries={queries} />

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
