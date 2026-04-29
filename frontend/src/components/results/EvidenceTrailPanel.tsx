"use client";

import { useEffect, useState } from "react";
import type { EvidenceTrail } from "@/types/api";
import LoadingSpinner from "@/components/LoadingSpinner";
import ErrorAlert from "@/components/ErrorAlert";

interface EvidenceTrailPanelProps {
  candidateUuid: string;
  openalexConcepts?: string[];
}

export default function EvidenceTrailPanel({ candidateUuid, openalexConcepts }: EvidenceTrailPanelProps) {
  const [evidence, setEvidence] = useState<EvidenceTrail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeSource, setActiveSource] = useState<string>("all");

  useEffect(() => {
    const fetchEvidence = async () => {
      setLoading(true);
      setError(null);
      try {
        const response = await fetch(`/api/candidates/${candidateUuid}/evidence`);
        if (!response.ok) {
          throw new Error(`Failed to fetch evidence: ${response.status}`);
        }
        const data: EvidenceTrail = await response.json();
        setEvidence(data);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to load evidence trail.");
      } finally {
        setLoading(false);
      }
    };

    fetchEvidence();
  }, [candidateUuid]);

  if (loading) return <LoadingSpinner message="Loading evidence trail..." />;
  if (error) return <ErrorAlert message={error} />;
  if (!evidence) return null;

  const allSources = Array.from(new Set(evidence.evidence_items.map((i) => i.source))).sort();
  const visible =
    activeSource === "all"
      ? evidence.evidence_items
      : evidence.evidence_items.filter((i) => i.source === activeSource);

  // Sort by date for timeline view
  const sortedVisible = [...visible].sort((a, b) => {
    if (!a.date && !b.date) return 0;
    if (!a.date) return 1;
    if (!b.date) return -1;
    return b.date.localeCompare(a.date);
  });

  const SOURCE_LABELS: Record<string, string> = {
    pubmed: "PubMed",
    icite: "iCite",
    reporter: "NIH Grants",
    erc: "ERC",
    mrc: "MRC",
    cihr: "CIHR",
    kaken: "KAKEN",
    clinicaltrials: "Trials",
    aegis: "Notes",
  };

  return (
    <div className="bg-gray-50 border-t border-gray-200 px-6 py-4">
      <div className="flex items-center justify-between mb-3">
        <h4 className="text-sm font-semibold text-gray-900">
          Evidence Trail — {evidence.candidate_name}
        </h4>
        {allSources.length > 1 && (
          <div className="flex items-center gap-1 flex-wrap">
            <button
              onClick={() => setActiveSource("all")}
              className={`px-2 py-0.5 rounded text-xs font-medium transition-colors ${
                activeSource === "all"
                  ? "bg-blue-600 text-white"
                  : "bg-gray-200 text-gray-600 hover:bg-gray-300"
              }`}
            >
              All ({evidence.evidence_items.length})
            </button>
            {allSources.map((src) => {
              const count = evidence.evidence_items.filter((i) => i.source === src).length;
              return (
                <button
                  key={src}
                  onClick={() => setActiveSource(src)}
                  className={`px-2 py-0.5 rounded text-xs font-medium transition-colors ${
                    activeSource === src
                      ? "bg-blue-600 text-white"
                      : "bg-gray-200 text-gray-600 hover:bg-gray-300"
                  }`}
                >
                  {SOURCE_LABELS[src] ?? src} ({count})
                </button>
              );
            })}
          </div>
        )}
      </div>

      {/* OpenAlex concepts */}
      {openalexConcepts && openalexConcepts.length > 0 && (
        <div className="mb-3">
          <h5 className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-1">OpenAlex Concepts</h5>
          <div className="flex flex-wrap gap-1">
            {openalexConcepts.map((concept) => (
              <span
                key={concept}
                className="inline-flex items-center rounded-full bg-indigo-100 px-2 py-0.5 text-xs font-medium text-indigo-700"
              >
                {concept}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* Why ranked here */}
      {evidence.evidence_items.length > 0 && (
        <div className="mb-3 rounded-md bg-blue-50 border border-blue-200 p-3">
          <h5 className="text-xs font-semibold text-blue-700 uppercase tracking-wider mb-1">Why Ranked Here?</h5>
          <p className="text-sm text-blue-800">
            This candidate was ranked based on {evidence.evidence_items.length} evidence items
            from {allSources.length} source{allSources.length !== 1 ? "s" : ""}: {allSources.map((s) => SOURCE_LABELS[s] ?? s).join(", ")}.
          </p>
        </div>
      )}

      {/* Timeline */}
      {sortedVisible.length === 0 ? (
        <p className="text-sm text-gray-500">No evidence items available.</p>
      ) : (
        <div className="space-y-3">
          {sortedVisible.map((item, index) => (
            <div key={index} className="flex items-start space-x-3 text-sm">
              {/* Timeline dot */}
              <div className="flex-shrink-0 mt-1.5">
                <div className="w-2 h-2 rounded-full bg-blue-400" />
              </div>
              <span className="inline-flex items-center rounded bg-gray-200 px-2 py-0.5 text-xs font-medium text-gray-700 whitespace-nowrap">
                {item.type}
              </span>
              <div className="flex-1">
                <p className="text-gray-900">{item.description}</p>
                <div className="flex items-center space-x-3 mt-1 text-xs text-gray-500">
                  <span className="font-medium text-gray-400 uppercase tracking-wide">{SOURCE_LABELS[item.source] ?? item.source}</span>
                  {item.date && <span>{item.date}</span>}
                  {item.score_contribution !== undefined && (
                    <span>contribution {item.score_contribution.toFixed(3)}</span>
                  )}
                </div>
                {item.url && (
                  <a
                    href={item.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-xs text-blue-600 hover:text-blue-500 mt-1 inline-block"
                  >
                    View source
                  </a>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
