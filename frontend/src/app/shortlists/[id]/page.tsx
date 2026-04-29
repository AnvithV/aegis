"use client";

import { useCallback, useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import type { Shortlist, ShortlistMember } from "@/types/api";
import LoadingSpinner from "@/components/LoadingSpinner";
import ErrorAlert from "@/components/ErrorAlert";
import ExportButton from "@/components/shortlists/ExportButton";

interface ShortlistDetail extends Shortlist {
  members?: ShortlistMember[];
}

export default function ShortlistDetailPage() {
  const params = useParams();
  const shortlistId = params.id as string;

  const [shortlist, setShortlist] = useState<ShortlistDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchDetail = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await fetch(`/api/shortlists/${shortlistId}`);
      if (!response.ok) {
        throw new Error(`Failed to load shortlist: ${response.status}`);
      }
      const data: ShortlistDetail = await response.json();
      setShortlist(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load shortlist.");
    } finally {
      setLoading(false);
    }
  }, [shortlistId]);

  useEffect(() => {
    if (shortlistId) {
      fetchDetail();
    }
  }, [shortlistId, fetchDetail]);

  const handleRemoveMember = async (candidateUuid: string) => {
    try {
      await fetch(`/api/shortlists/${shortlistId}/candidates`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ action: "remove", candidate_uuid: candidateUuid }),
      });
      fetchDetail();
    } catch {
      // silently fail
    }
  };

  if (loading) return <LoadingSpinner message="Loading shortlist..." />;
  if (error) return <ErrorAlert message={error} onRetry={fetchDetail} />;
  if (!shortlist) return null;

  const members = shortlist.members ?? [];

  return (
    <div className="max-w-5xl mx-auto">
      <div className="mb-4">
        <Link href="/shortlists" className="text-sm text-blue-600 hover:text-blue-800">
          &larr; Back to shortlists
        </Link>
      </div>

      {/* Header */}
      <div className="bg-white border border-gray-200 rounded-lg p-6 mb-6">
        <div className="flex items-start justify-between">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">{shortlist.name}</h1>
            {shortlist.description && (
              <p className="text-sm text-gray-600 mt-1">{shortlist.description}</p>
            )}
            <div className="flex items-center gap-3 mt-2 text-xs text-gray-400">
              <span>{members.length} candidates</span>
              <span>Created by {shortlist.created_by}</span>
              <span>{new Date(shortlist.created_at).toLocaleDateString()}</span>
            </div>
          </div>
          <ExportButton shortlistId={shortlistId} members={members} shortlistName={shortlist.name} />
        </div>
      </div>

      {/* Members list */}
      {members.length === 0 ? (
        <div className="text-center py-12 bg-white rounded-lg border border-gray-200">
          <p className="text-gray-500">No candidates in this shortlist yet.</p>
          <p className="text-sm text-gray-400 mt-1">Add candidates from the results page.</p>
        </div>
      ) : (
        <div className="bg-white border border-gray-200 rounded-lg overflow-hidden">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Candidate
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Added By
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Added At
                </th>
                <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Actions
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200">
              {members.map((member) => (
                <tr key={member.candidate_uuid} className="hover:bg-gray-50 transition-colors">
                  <td className="px-6 py-4 text-sm">
                    <Link
                      href={`/candidates/${member.candidate_uuid}`}
                      className="text-blue-600 hover:text-blue-800 font-medium"
                    >
                      {member.candidate_name ?? member.candidate_uuid}
                    </Link>
                  </td>
                  <td className="px-6 py-4 text-sm text-gray-500">{member.added_by}</td>
                  <td className="px-6 py-4 text-sm text-gray-500">
                    {new Date(member.added_at).toLocaleString()}
                  </td>
                  <td className="px-6 py-4 text-sm text-right">
                    <button
                      onClick={() => handleRemoveMember(member.candidate_uuid)}
                      className="text-red-600 hover:text-red-800 text-xs font-medium"
                    >
                      Remove
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
