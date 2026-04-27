"use client";

import { useEffect, useState } from "react";
import type { EvidenceTrail } from "@/types/api";
import LoadingSpinner from "@/components/LoadingSpinner";
import ErrorAlert from "@/components/ErrorAlert";

interface EvidenceTrailPanelProps {
  candidateUuid: string;
}

export default function EvidenceTrailPanel({ candidateUuid }: EvidenceTrailPanelProps) {
  const [evidence, setEvidence] = useState<EvidenceTrail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

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

  return (
    <div className="bg-gray-50 border-t border-gray-200 px-6 py-4">
      <h4 className="text-sm font-semibold text-gray-900 mb-3">
        Evidence Trail for {evidence.candidate_name}
      </h4>
      {evidence.evidence_items.length === 0 ? (
        <p className="text-sm text-gray-500">No evidence items available.</p>
      ) : (
        <div className="space-y-3">
          {evidence.evidence_items.map((item, index) => (
            <div key={index} className="flex items-start space-x-3 text-sm">
              <span className="inline-flex items-center rounded bg-gray-200 px-2 py-0.5 text-xs font-medium text-gray-700 whitespace-nowrap">
                {item.type}
              </span>
              <div className="flex-1">
                <p className="text-gray-900">{item.description}</p>
                <div className="flex items-center space-x-3 mt-1 text-xs text-gray-500">
                  <span>Source: {item.source}</span>
                  {item.date && <span>Date: {item.date}</span>}
                  {item.score_contribution !== undefined && (
                    <span>Contribution: {item.score_contribution.toFixed(3)}</span>
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
