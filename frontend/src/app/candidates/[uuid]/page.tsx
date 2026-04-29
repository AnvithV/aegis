"use client";

import { useCallback, useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import type { EvidenceTrail, CandidateNote } from "@/types/api";
import LoadingSpinner from "@/components/LoadingSpinner";
import ErrorAlert from "@/components/ErrorAlert";
import CandidateTimeline from "@/components/candidates/CandidateTimeline";
import ScoreHistoryChart from "@/components/candidates/ScoreHistoryChart";
import AnalystNotes from "@/components/candidates/AnalystNotes";

interface CandidateProfileData {
  candidate_uuid: string;
  candidate_name: string;
  affiliation?: string;
  country?: string | null;
  identity_linkage_confidence?: number;
  integrity_status?: string;
  integrity_disclosures?: string[];
  f1_f7_scores?: Record<string, number>;
  score_history?: Array<{ query_id: string; score: number; rank: number; date: string; task_description?: string }>;
  evidence_items: EvidenceTrail["evidence_items"];
}

export default function CandidateProfilePage() {
  const params = useParams();
  const uuid = params.uuid as string;

  const [profile, setProfile] = useState<CandidateProfileData | null>(null);
  const [notes, setNotes] = useState<CandidateNote[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchProfile = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await fetch(`/api/candidates/${uuid}/evidence`);
      if (!response.ok) {
        throw new Error(`Failed to load candidate profile: ${response.status}`);
      }
      const data: CandidateProfileData = await response.json();
      setProfile(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load profile.");
    } finally {
      setLoading(false);
    }
  }, [uuid]);

  const fetchNotes = useCallback(async () => {
    try {
      const response = await fetch(`/api/candidates/${uuid}/notes`);
      if (response.ok) {
        const data: CandidateNote[] = await response.json();
        setNotes(data);
      }
    } catch {
      // Notes are optional; silently fail
    }
  }, [uuid]);

  useEffect(() => {
    if (uuid) {
      fetchProfile();
      fetchNotes();
    }
  }, [uuid, fetchProfile, fetchNotes]);

  if (loading) return <LoadingSpinner message="Loading candidate profile..." />;
  if (error) return <ErrorAlert message={error} onRetry={fetchProfile} />;
  if (!profile) return null;

  const hasIntegrityIssues =
    (profile.integrity_disclosures && profile.integrity_disclosures.length > 0) ||
    profile.integrity_status === "flagged";

  const f1f7Labels: Record<string, string> = {
    f1_rcr: "F1 RCR",
    f2_funding: "F2 Funding",
    f3_leadership: "F3 Leadership",
    f4_apex: "F4 Apex",
    f5_translational: "F5 Translational",
    f6_lineage: "F6 Lineage",
    f7_clinician: "F7 Clinician",
  };

  return (
    <div className="max-w-5xl mx-auto">
      {/* Back link */}
      <div className="mb-4">
        <Link href="/history" className="text-sm text-blue-600 hover:text-blue-800">
          &larr; Back to queries
        </Link>
      </div>

      {/* Candidate header */}
      <div className="bg-white border border-gray-200 rounded-lg p-6 mb-6">
        <div className="flex items-start justify-between">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">{profile.candidate_name}</h1>
            {profile.affiliation && (
              <p className="text-sm text-gray-600 mt-1">{profile.affiliation}</p>
            )}
            {profile.country && (
              <p className="text-sm text-gray-500">{profile.country}</p>
            )}
            {profile.identity_linkage_confidence !== undefined && (
              <p className="text-xs text-gray-400 mt-1">
                Identity confidence: {(profile.identity_linkage_confidence * 100).toFixed(1)}%
              </p>
            )}
          </div>
          <button
            onClick={() => window.print()}
            className="px-4 py-2 rounded-md bg-white border border-gray-300 text-sm font-medium text-gray-700 hover:bg-gray-50 shadow-sm transition-colors print:hidden"
          >
            Export as PDF Brief
          </button>
        </div>

        {/* Integrity banner */}
        {hasIntegrityIssues ? (
          <div className="mt-4 rounded-md bg-red-50 border border-red-200 p-3">
            <p className="text-sm font-medium text-red-800">Integrity Issues Found</p>
            {profile.integrity_disclosures?.map((d, i) => (
              <p key={i} className="text-sm text-red-600 mt-1">{d}</p>
            ))}
          </div>
        ) : (
          <div className="mt-4 rounded-md bg-green-50 border border-green-200 p-3">
            <p className="text-sm font-medium text-green-800">No integrity issues</p>
          </div>
        )}
      </div>

      {/* F1-F7 scores */}
      {profile.f1_f7_scores && Object.keys(profile.f1_f7_scores).length > 0 && (
        <div className="bg-white border border-gray-200 rounded-lg p-6 mb-6">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">Score Breakdown (F1-F7)</h2>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
            {Object.entries(profile.f1_f7_scores).map(([key, value]) => (
              <div key={key} className="text-center p-3 bg-gray-50 rounded-lg">
                <p className="text-xs text-gray-500 uppercase">{f1f7Labels[key] ?? key}</p>
                <p className="text-lg font-bold text-gray-900">{(value as number).toFixed(3)}</p>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Score history chart */}
      {profile.score_history && profile.score_history.length > 0 && (
        <div className="bg-white border border-gray-200 rounded-lg p-6 mb-6">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">Score History</h2>
          <ScoreHistoryChart history={profile.score_history} />
        </div>
      )}

      {/* Candidate timeline */}
      <div className="bg-white border border-gray-200 rounded-lg p-6 mb-6">
        <h2 className="text-lg font-semibold text-gray-900 mb-4">Evidence Timeline</h2>
        <CandidateTimeline evidenceItems={profile.evidence_items} />
      </div>

      {/* Analyst notes */}
      <div className="bg-white border border-gray-200 rounded-lg p-6 mb-6 print:hidden">
        <h2 className="text-lg font-semibold text-gray-900 mb-4">Analyst Notes</h2>
        <AnalystNotes candidateUuid={uuid} notes={notes} onNotesChange={fetchNotes} />
      </div>
    </div>
  );
}
