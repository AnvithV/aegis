"use client";

import { useState } from "react";
import type { CandidateResult } from "@/types/api";
import ScoreBreakdownChart from "./ScoreBreakdownChart";
import ArtifactChip from "./ArtifactChip";
import VarianceBand from "./VarianceBand";
import IntegrityBadge from "./IntegrityBadge";
import EvidenceTrailPanel from "./EvidenceTrailPanel";

interface CandidateRowProps {
  candidate: CandidateResult;
}

export default function CandidateRow({ candidate }: CandidateRowProps) {
  const [isExpanded, setIsExpanded] = useState(false);

  return (
    <div className="bg-white border border-gray-200 rounded-lg overflow-hidden">
      <div
        className="px-6 py-4 cursor-pointer hover:bg-gray-50 transition-colors"
        onClick={() => setIsExpanded(!isExpanded)}
      >
        <div className="flex items-start justify-between">
          <div className="flex items-start space-x-4">
            {/* Rank badge */}
            <div className="flex-shrink-0 w-10 h-10 rounded-full bg-blue-600 text-white flex items-center justify-center font-bold text-sm">
              #{candidate.rank}
            </div>

            {/* Candidate info */}
            <div className="min-w-0 flex-1">
              <div className="flex items-center space-x-2">
                <h3 className="text-sm font-semibold text-gray-900">{candidate.name}</h3>
                <span className="inline-flex items-center rounded-full bg-gray-100 px-2 py-0.5 text-xs text-gray-600">
                  {candidate.specialty}
                </span>
              </div>
              <p className="text-sm text-gray-500 mt-0.5">{candidate.affiliation}</p>

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

          {/* Score section */}
          <div className="flex-shrink-0 ml-4 text-right">
            <VarianceBand
              score={candidate.score}
              band={candidate.score_variance_band}
            />
            <div className="mt-2 w-48">
              <ScoreBreakdownChart components={candidate.score_components} />
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

      {/* Evidence trail panel (expanded) */}
      {isExpanded && <EvidenceTrailPanel candidateUuid={candidate.uuid} />}
    </div>
  );
}
