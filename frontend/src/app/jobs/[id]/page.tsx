"use client";

import { useState, useEffect, useCallback } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import type { JobRecord } from "@/types/api";

const SOURCE_NAMES = ["pubmed", "reporter", "ctgov", "openalex_works"];
const SOURCE_LABELS: Record<string, string> = {
  pubmed: "PubMed",
  reporter: "NIH Reporter",
  ctgov: "CT.gov",
  openalex_works: "OpenAlex",
};

interface SourceData {
  status: string;
  record_count?: number;
}

function formatRelativeTime(dateStr: string): string {
  const diff = Date.now() - new Date(dateStr).getTime();
  const seconds = Math.floor(diff / 1000);
  if (seconds < 60) return "Just now";
  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) return `${minutes} minutes ago`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours} hours ago`;
  const days = Math.floor(hours / 24);
  return `${days} days ago`;
}

function StatusBadge({ status }: { status: string }) {
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
      {c.label}
    </span>
  );
}

function SourceCard({ name, data }: { name: string; data?: SourceData }) {
  const st = data?.status || "pending";
  const bgColors: Record<string, string> = {
    pending: "bg-gray-50 border-gray-200",
    fetching: "bg-amber-50 border-amber-200",
    complete: "bg-green-50 border-green-200",
    failed: "bg-red-50 border-red-200",
  };
  return (
    <div className={`rounded-lg border p-3 text-center ${bgColors[st] || bgColors.pending}`}>
      <p className="text-sm font-medium text-gray-700">{SOURCE_LABELS[name] || name}</p>
      <p className="mt-1 text-xs text-gray-500">{st}</p>
      {st === "complete" && data?.record_count != null && (
        <p className="mt-1 text-xs font-semibold text-green-700">{data.record_count} records</p>
      )}
      {st === "fetching" && (
        <div className="mt-1 h-1 bg-amber-200 rounded-full overflow-hidden">
          <div className="h-full bg-amber-400 rounded-full animate-pulse" style={{ width: "60%" }} />
        </div>
      )}
    </div>
  );
}

export default function JobDetailPage() {
  const params = useParams();
  const id = params.id as string;

  const [job, setJob] = useState<JobRecord | null>(null);
  const [sources, setSources] = useState<Map<string, SourceData>>(new Map());
  const [loading, setLoading] = useState(true);
  const [cancelling, setCancelling] = useState(false);

  const fetchJob = useCallback(async () => {
    try {
      const response = await fetch(`/api/jobs/${id}`);
      if (!response.ok) throw new Error(`Failed to load job: ${response.status}`);
      const data: JobRecord = await response.json();
      setJob(data);
    } catch {
      // silently fail on refetch
    } finally {
      setLoading(false);
    }
  }, [id]);

  useEffect(() => {
    fetchJob();
  }, [fetchJob]);

  // SSE subscription for in_progress jobs
  useEffect(() => {
    if (job?.status !== "in_progress") return;
    const es = new EventSource(`/api/queries/${id}/stream`);
    es.addEventListener("source_progress", (e) => {
      const data = JSON.parse(e.data);
      setSources((prev) => new Map(prev).set(data.source_name, data));
    });
    es.addEventListener("complete", () => {
      es.close();
      fetchJob();
    });
    es.addEventListener("error", () => {
      es.close();
    });
    return () => es.close();
  }, [job?.status, id, fetchJob]);

  const handleCancel = async () => {
    setCancelling(true);
    try {
      await fetch(`/api/jobs/${id}`, { method: "POST" });
      await fetchJob();
    } catch {
      // ignore cancel errors
    } finally {
      setCancelling(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <svg className="animate-spin h-6 w-6 text-gray-400" fill="none" viewBox="0 0 24 24">
          <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
          <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
        </svg>
        <span className="ml-2 text-sm text-gray-500">Loading job details...</span>
      </div>
    );
  }

  if (!job) {
    return (
      <div className="text-center py-12">
        <p className="text-gray-500">Job not found.</p>
        <Link href="/jobs" className="mt-4 inline-block text-sm font-medium text-blue-600 hover:text-blue-800">
          &larr; Back to Jobs
        </Link>
      </div>
    );
  }

  return (
    <div>
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <Link href="/jobs" className="text-sm text-gray-500 hover:text-gray-700">
          &larr; Back to Jobs
        </Link>
        <div className="flex items-center gap-3">
          {job.status === "in_progress" && (
            <button
              onClick={handleCancel}
              disabled={cancelling}
              className="px-4 py-2 rounded-md border border-amber-300 text-sm font-medium text-amber-700 hover:bg-amber-50 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              {cancelling ? "Cancelling..." : "Cancel"}
            </button>
          )}
          {job.status === "complete" && (
            <Link
              href={`/results/${job.id}`}
              className="px-4 py-2 rounded-md bg-blue-600 text-white text-sm font-medium hover:bg-blue-700 transition-colors"
            >
              View Results &rarr;
            </Link>
          )}
        </div>
      </div>

      {/* Query info */}
      <div className="mb-6">
        <p className="text-sm text-gray-500 mb-1">Query</p>
        <p className="text-lg font-medium text-gray-900">&ldquo;{job.query_text}&rdquo;</p>
        <div className="flex items-center gap-4 mt-3">
          <StatusBadge status={job.status} />
          <span className="text-sm text-gray-500">Started: {formatRelativeTime(job.created_at)}</span>
          {job.candidate_count != null && (
            <span className="text-sm text-gray-500">{job.candidate_count} candidates</span>
          )}
        </div>
      </div>

      {/* Source progress grid */}
      <div className="mb-6">
        <h2 className="text-sm font-semibold text-gray-700 mb-3">Source Progress</h2>
        <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
          {SOURCE_NAMES.map((name) => (
            <SourceCard key={name} name={name} data={sources.get(name)} />
          ))}
        </div>
      </div>

      {/* Error banner */}
      {job.status === "failed" && (
        <div className="mt-6 rounded-md bg-red-50 border border-red-200 p-4">
          <p className="text-sm text-red-800">This job failed during execution. Please try submitting the query again.</p>
        </div>
      )}

      {/* Cancelled banner */}
      {job.status === "cancelled" && (
        <div className="mt-6 rounded-md bg-gray-50 border border-gray-200 p-4">
          <p className="text-sm text-gray-600">This job was cancelled.</p>
        </div>
      )}
    </div>
  );
}
