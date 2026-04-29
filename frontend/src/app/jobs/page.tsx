"use client";

import { useState, useEffect, useCallback } from "react";
import Link from "next/link";
import type { JobRecord, JobListResponse } from "@/types/api";

const PER_PAGE = 20;

function formatDuration(ms: number | null): string {
  if (ms == null) return "--";
  if (ms < 1000) return `${ms}ms`;
  return `${(ms / 1000).toFixed(1)}s`;
}

function formatRelativeTime(dateStr: string): string {
  const diff = Date.now() - new Date(dateStr).getTime();
  const seconds = Math.floor(diff / 1000);
  if (seconds < 60) return "Just now";
  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(hours / 24);
  return `${days} days ago`;
}

function StatusBadge({ status }: { status: JobRecord["status"] }) {
  const config: Record<string, { bg: string; label: string }> = {
    in_progress: { bg: "bg-amber-100 text-amber-800", label: "Running" },
    complete: { bg: "bg-green-100 text-green-800", label: "Complete" },
    failed: { bg: "bg-red-100 text-red-800", label: "Failed" },
    cancelled: { bg: "bg-gray-100 text-gray-600", label: "Cancelled" },
  };
  const c = config[status] || config.cancelled;
  return (
    <span className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ${c.bg}`}>
      {status === "in_progress" && (
        <svg className="animate-spin -ml-0.5 mr-1.5 h-3 w-3" fill="none" viewBox="0 0 24 24">
          <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
          <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
        </svg>
      )}
      {status === "complete" && (
        <svg className="-ml-0.5 mr-1 h-3 w-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
        </svg>
      )}
      {status === "failed" && (
        <svg className="-ml-0.5 mr-1 h-3 w-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
        </svg>
      )}
      {c.label}
    </span>
  );
}

export default function JobsPage() {
  const [jobs, setJobs] = useState<JobRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [currentPage, setCurrentPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);

  const fetchJobs = useCallback(async (page: number) => {
    setError(null);
    try {
      const response = await fetch(`/api/jobs?page=${page}&per_page=${PER_PAGE}`);
      if (!response.ok) {
        throw new Error(`Failed to load jobs: ${response.status}`);
      }
      const data: JobListResponse = await response.json();
      setJobs(data.jobs);
      setTotalPages(Math.max(1, Math.ceil(data.total / PER_PAGE)));
      setCurrentPage(page);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load jobs.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchJobs(1);
  }, [fetchJobs]);

  // Poll while any job is in_progress
  useEffect(() => {
    const hasActive = jobs.some((j) => j.status === "in_progress");
    if (!hasActive) return;
    const interval = setInterval(() => fetchJobs(currentPage), 3000);
    return () => clearInterval(interval);
  }, [jobs, currentPage, fetchJobs]);

  return (
    <div>
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Jobs</h1>
        <p className="mt-2 text-sm text-gray-600">
          Track the progress of your expert discovery queries.
        </p>
      </div>

      {loading ? (
        <div className="flex items-center justify-center py-12">
          <svg className="animate-spin h-6 w-6 text-gray-400" fill="none" viewBox="0 0 24 24">
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
          </svg>
          <span className="ml-2 text-sm text-gray-500">Loading jobs...</span>
        </div>
      ) : error ? (
        <div className="rounded-md bg-red-50 p-4">
          <p className="text-sm text-red-700">{error}</p>
          <button
            onClick={() => fetchJobs(currentPage)}
            className="mt-2 text-sm text-red-600 underline hover:text-red-800"
          >
            Retry
          </button>
        </div>
      ) : jobs.length === 0 ? (
        <div className="text-center py-12">
          <p className="text-gray-500">No jobs yet. Submit a query to get started.</p>
          <Link
            href="/"
            className="mt-4 inline-block text-sm font-medium text-blue-600 hover:text-blue-800"
          >
            New Query &rarr;
          </Link>
        </div>
      ) : (
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 overflow-hidden">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Query</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Status</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Started</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Duration</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Candidates</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Actions</th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {jobs.map((job) => (
                <tr key={job.id} className="hover:bg-gray-50">
                  <td className="px-6 py-4 text-sm text-gray-900 max-w-xs truncate">
                    {job.query_text}
                  </td>
                  <td className="px-6 py-4">
                    <StatusBadge status={job.status} />
                    {job.status === "in_progress" && (
                      <div className="mt-1 h-1 w-full bg-amber-200 rounded-full overflow-hidden">
                        <div className="h-full bg-amber-500 rounded-full animate-pulse" style={{ width: "60%" }} />
                      </div>
                    )}
                  </td>
                  <td className="px-6 py-4 text-sm text-gray-500">
                    {formatRelativeTime(job.created_at)}
                  </td>
                  <td className="px-6 py-4 text-sm text-gray-500">
                    {formatDuration(job.duration_ms)}
                  </td>
                  <td className="px-6 py-4 text-sm text-gray-500">
                    {job.candidate_count != null ? job.candidate_count : "--"}
                  </td>
                  <td className="px-6 py-4 text-sm">
                    {job.status === "complete" && (
                      <Link
                        href={`/results/${job.id}`}
                        className="text-blue-600 hover:text-blue-800 font-medium"
                      >
                        View Results &rarr;
                      </Link>
                    )}
                    {job.status === "in_progress" && (
                      <Link
                        href={`/jobs/${job.id}`}
                        className="text-amber-600 hover:text-amber-800 font-medium"
                      >
                        Monitor &rarr;
                      </Link>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>

          {totalPages > 1 && (
            <div className="flex items-center justify-between px-6 py-3 bg-gray-50 border-t border-gray-200">
              <button
                onClick={() => fetchJobs(currentPage - 1)}
                disabled={currentPage <= 1}
                className="px-3 py-1 rounded-md border border-gray-300 text-sm text-gray-700 hover:bg-white disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              >
                Previous
              </button>
              <span className="text-sm text-gray-600">
                Page {currentPage} of {totalPages}
              </span>
              <button
                onClick={() => fetchJobs(currentPage + 1)}
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
