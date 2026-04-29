"use client";

import { useState } from "react";
import Link from "next/link";
import type { CandidateResult } from "@/types/api";
import ScoreBreakdownChart from "./ScoreBreakdownChart";
import ArtifactChip from "./ArtifactChip";
import VarianceBand from "./VarianceBand";
import IntegrityBadge from "./IntegrityBadge";
import EvidenceTrailPanel from "./EvidenceTrailPanel";

const SOURCE_BADGE_COLORS: Record<string, string> = {
  pubmed: "bg-blue-400",
  icite: "bg-cyan-400",
  reporter: "bg-green-400",
  ctgov: "bg-purple-400",
  openalex: "bg-orange-400",
  leie: "bg-red-400",
  uspto: "bg-yellow-400",
  epo: "bg-indigo-400",
};

interface CandidateRowProps {
  candidate: CandidateResult;
  isCompareSelected?: boolean;
  onToggleCompare?: () => void;
}

export default function CandidateRow({
  candidate,
  isCompareSelected,
  onToggleCompare,
}: CandidateRowProps) {
  const [isExpanded, setIsExpanded] = useState(false);
  const [isShortlisted, setIsShortlisted] = useState(false);

  const f1f7 = candidate.score_components;

  return (
    <div className="bg-white border border-gray-200 rounded-lg overflow-hidden">
      <div
        className="px-6 py-4 cursor-pointer hover:bg-gray-50 transition-colors"
        onClick={() => setIsExpanded(!isExpanded)}
      >
        <div className="flex items-start justify-between">
          <div className="flex items-start space-x-4">
            {/* Compare checkbox */}
            {onToggleCompare && (
              <div className="flex-shrink-0 pt-2" onClick={(e) => e.stopPropagation()}>
                <input
                  type="checkbox"
                  checked={isCompareSelected ?? false}
                  onChange={onToggleCompare}
                  className="h-4 w-4 rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                  title="Select for comparison"
                />
              </div>
            )}

            {/* Rank badge */}
            <div className="flex-shrink-0 w-10 h-10 rounded-full bg-blue-600 text-white flex items-center justify-center font-bold text-sm">
              #{candidate.rank}
            </div>

            {/* Candidate info */}
            <div className="min-w-0 flex-1">
              <div className="flex items-center space-x-2">
                <Link
                  href={`/candidates/${candidate.uuid}`}
                  onClick={(e) => e.stopPropagation()}
                  className="text-sm font-semibold text-blue-700 hover:text-blue-900 hover:underline"
                >
                  {candidate.name}
                </Link>
                <span className="inline-flex items-center rounded-full bg-gray-100 px-2 py-0.5 text-xs text-gray-600">
                  {candidate.specialty}
                </span>
                {/* Notes indicator */}
                {candidate.has_notes && (
                  <span className="text-yellow-500" title="Has analyst notes">
                    <svg className="h-4 w-4" fill="currentColor" viewBox="0 0 20 20">
                      <path d="M18 13V5a2 2 0 00-2-2H4a2 2 0 00-2 2v8a2 2 0 002 2h3l3 3 3-3h3a2 2 0 002-2z" />
                    </svg>
                  </span>
                )}
                {/* Analyst avatar badges */}
                {candidate.shortlisted_by && candidate.shortlisted_by.length > 0 && (
                  <div className="flex -space-x-1">
                    {candidate.shortlisted_by.map((analyst) => {
                      const initials = analyst
                        .split(/\s+/)
                        .map((w) => w[0])
                        .join("")
                        .toUpperCase()
                        .slice(0, 2);
                      // Deterministic color from name
                      const colors = [
                        "bg-blue-500", "bg-green-500", "bg-purple-500",
                        "bg-pink-500", "bg-amber-500", "bg-cyan-500",
                      ];
                      const colorIdx = analyst.split("").reduce((sum, c) => sum + c.charCodeAt(0), 0) % colors.length;
                      return (
                        <span
                          key={analyst}
                          title={`Shortlisted by ${analyst}`}
                          className={`inline-flex items-center justify-center w-5 h-5 rounded-full text-white text-[10px] font-bold ring-2 ring-white ${colors[colorIdx]}`}
                        >
                          {initials}
                        </span>
                      );
                    })}
                  </div>
                )}
              </div>
              <p className="text-sm text-gray-500 mt-0.5">{candidate.affiliation}</p>

              {/* Source badges */}
              {candidate.source_badges && candidate.source_badges.length > 0 && (
                <div className="flex gap-1 mt-1">
                  {candidate.source_badges.map((src) => (
                    <span
                      key={src}
                      className={`inline-block w-2 h-2 rounded-full ${SOURCE_BADGE_COLORS[src] ?? "bg-gray-400"}`}
                      title={src}
                    />
                  ))}
                </div>
              )}

              {/* Identity linkage confidence */}
              <p className="text-xs text-gray-400 mt-1">
                Identity confidence: {(candidate.identity_linkage_confidence * 100).toFixed(1)}%
              </p>

              {/* Integrity disclosures */}
              <IntegrityBadge disclosures={candidate.integrity_disclosures} />

              {/* Top artifacts */}
              <div className="flex flex-wrap gap-1.5 mt-2">
                {candidate.top_artifacts.slice(0, 3).map((artifact) => (
                  <ArtifactChip key={artifact.id} artifact={artifact} />
                ))}
              </div>
            </div>
          </div>

          {/* Score section + actions */}
          <div className="flex-shrink-0 ml-4 flex items-start gap-3">
            {/* Shortlist star */}
            <button
              type="button"
              onClick={(e) => {
                e.stopPropagation();
                setIsShortlisted(!isShortlisted);
              }}
              className={`p-1 rounded hover:bg-gray-100 ${isShortlisted ? "text-yellow-500" : "text-gray-300"}`}
              title={isShortlisted ? "Remove from shortlist" : "Add to shortlist"}
            >
              <svg className="h-5 w-5" fill={isShortlisted ? "currentColor" : "none"} viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11.049 2.927c.3-.921 1.603-.921 1.902 0l1.519 4.674a1 1 0 00.95.69h4.915c.969 0 1.371 1.24.588 1.81l-3.976 2.888a1 1 0 00-.363 1.118l1.518 4.674c.3.922-.755 1.688-1.538 1.118l-3.976-2.888a1 1 0 00-1.176 0l-3.976 2.888c-.783.57-1.838-.197-1.538-1.118l1.518-4.674a1 1 0 00-.363-1.118l-3.976-2.888c-.784-.57-.38-1.81.588-1.81h4.914a1 1 0 00.951-.69l1.519-4.674z" />
              </svg>
            </button>

            <div className="text-right">
              <VarianceBand
                score={candidate.score}
                band={candidate.score_variance_band}
              />
              <div className="mt-2 w-48">
                <ScoreBreakdownChart components={candidate.score_components} />
              </div>
            </div>
          </div>
        </div>

        {/* Expand indicator */}
        <div className="flex justify-center mt-2">
          <svg
            className={`h-4 w-4 text-gray-400 transition-transform ${isExpanded ? "rotate-180" : ""}`}
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
          >
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
          </svg>
        </div>
      </div>

      {/* Expanded view: F1-F7 breakdown + evidence */}
      {isExpanded && (
        <div>
          {/* F1-F7 scores */}
          {(f1f7.f1_rcr !== undefined || f1f7.f2_funding !== undefined) && (
            <div className="border-t border-gray-200 px-6 py-3 bg-gray-50">
              <h4 className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-2">F1-F7 Component Scores</h4>
              <div className="flex flex-wrap gap-3">
                {[
                  { key: "f1_rcr", label: "F1 RCR" },
                  { key: "f2_funding", label: "F2 Funding" },
                  { key: "f3_leadership", label: "F3 Leadership" },
                  { key: "f4_apex", label: "F4 Apex" },
                  { key: "f5_translational", label: "F5 Translational" },
                  { key: "f6_lineage", label: "F6 Lineage" },
                  { key: "f7_clinician", label: "F7 Clinician" },
                ].map(({ key, label }) => {
                  const val = f1f7[key as keyof typeof f1f7];
                  if (val === undefined) return null;
                  return (
                    <div key={key} className="bg-white rounded px-2 py-1 border border-gray-200 text-xs">
                      <span className="text-gray-500">{label}</span>
                      <span className="ml-1 font-mono font-medium text-gray-800">
                        {(val as number).toFixed(3)}
                      </span>
                    </div>
                  );
                })}
              </div>
            </div>
          )}
          <EvidenceTrailPanel
            candidateUuid={candidate.uuid}
            openalexConcepts={candidate.openalex_concepts}
          />
        </div>
      )}
    </div>
  );
}
