"use client";

import { useCallback, useEffect, useState, useMemo } from "react";
import { useParams } from "next/navigation";
import type { QueryResponse, CandidateResult } from "@/types/api";
import { useSSE } from "@/hooks/useSSE";
import LoadingSpinner from "@/components/LoadingSpinner";
import ErrorAlert from "@/components/ErrorAlert";
import CandidateRow from "@/components/results/CandidateRow";
import FeedbackModal from "@/components/results/FeedbackModal";
import SourceProgressBar from "@/components/results/SourceProgressBar";
import WeightSliderPanel from "@/components/results/WeightSliderPanel";
import QueryTypeBadge from "@/components/results/QueryTypeBadge";
import CandidateComparisonModal from "@/components/results/CandidateComparisonModal";

export default function ResultsPage() {
  const params = useParams();
  const queryId = params.id as string;

  const [query, setQuery] = useState<QueryResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showFeedback, setShowFeedback] = useState(false);
  const [feedbackSubmitted, setFeedbackSubmitted] = useState(false);
  const [selectedForCompare, setSelectedForCompare] = useState<Set<string>>(new Set());
  const [showComparison, setShowComparison] = useState(false);
  const [exponents, setExponents] = useState<Record<string, number>>({
    alpha: 1,
    beta: 1,
    gamma: 1,
  });
  const [judgments, setJudgments] = useState<Record<string, "relevant" | "irrelevant">>({});

  const sseState = useSSE({ queryId, enabled: loading });

  const fetchQuery = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await fetch(`/api/queries/${queryId}`);
      if (!response.ok) {
        throw new Error(`Failed to load query results: ${response.status}`);
      }
      const data: QueryResponse = await response.json();

      // Fetch team collaboration data (shortlist membership + note flags)
      try {
        const shortlistedBy = new Map<string, string[]>();
        const hasNotes = new Map<string, boolean>();

        // Fetch shortlists for membership info
        const slResponse = await fetch("/api/shortlists").catch(() => null);
        if (slResponse && slResponse.ok) {
          const shortlists = await slResponse.json();
          const slArray = Array.isArray(shortlists) ? shortlists : shortlists.shortlists ?? [];
          for (const sl of slArray) {
            if (sl.members) {
              for (const member of sl.members as Array<{ candidate_uuid: string; added_by: string }>) {
                const existing = shortlistedBy.get(member.candidate_uuid) ?? [];
                if (!existing.includes(member.added_by)) {
                  existing.push(member.added_by);
                }
                shortlistedBy.set(member.candidate_uuid, existing);
              }
            }
          }
        }

        // Fetch notes existence for each candidate
        const noteChecks = await Promise.allSettled(
          data.candidates.map((c) => fetch(`/api/candidates/${c.uuid}/notes`))
        );
        for (let i = 0; i < data.candidates.length; i++) {
          const result = noteChecks[i];
          if (result.status === "fulfilled" && result.value.ok) {
            try {
              const notes = await result.value.json();
              const noteArray = Array.isArray(notes) ? notes : [];
              hasNotes.set(data.candidates[i].uuid, noteArray.length > 0);
            } catch {
              // ignore parse errors
            }
          }
        }

        // Merge into candidates
        data.candidates = data.candidates.map((c) => ({
          ...c,
          shortlisted_by: shortlistedBy.get(c.uuid) ?? c.shortlisted_by,
          has_notes: hasNotes.get(c.uuid) ?? c.has_notes,
        }));
      } catch {
        // Team data is optional; silently fail
      }

      setQuery(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load results.");
    } finally {
      setLoading(false);
    }
  }, [queryId]);

  useEffect(() => {
    if (queryId) {
      fetchQuery();
      // Load existing judgments for this query
      fetch(`/api/feedback/candidates/judgments/${queryId}`)
        .then((r) => r.json())
        .then((data) => {
          if (data.judgments) setJudgments(data.judgments);
        })
        .catch(() => {});
    }
  }, [queryId, fetchQuery]);

  const handleJudge = useCallback(
    async (uuid: string, judgment: "relevant" | "irrelevant") => {
      // Toggle off if already set to the same judgment
      if (judgments[uuid] === judgment) return;

      setJudgments((prev) => ({ ...prev, [uuid]: judgment }));

      const candidate = query?.candidates.find((c) => c.uuid === uuid);
      try {
        await fetch("/api/feedback/candidates/judge", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            query_id: queryId,
            candidate_uuid: uuid,
            judgment,
            score_components: candidate?.score_components ?? {},
          }),
        });
      } catch {
        // Revert on failure
        setJudgments((prev) => {
          const next = { ...prev };
          delete next[uuid];
          return next;
        });
      }
    },
    [queryId, query, judgments]
  );

  // Client-side re-ranking when exponents change
  const rankedCandidates = useMemo(() => {
    if (!query) return [];
    const candidates = [...query.candidates];
    candidates.sort((a, b) => {
      const scoreA =
        Math.pow(a.score_components.Q, exponents.alpha ?? 1) *
        Math.pow(a.score_components.C, exponents.beta ?? 1) *
        Math.pow(a.score_components.R, exponents.gamma ?? 1);
      const scoreB =
        Math.pow(b.score_components.Q, exponents.alpha ?? 1) *
        Math.pow(b.score_components.C, exponents.beta ?? 1) *
        Math.pow(b.score_components.R, exponents.gamma ?? 1);
      return scoreB - scoreA;
    });
    return candidates.map((c, i) => ({ ...c, rank: i + 1 }));
  }, [query, exponents]);

  // Geographic concentration warning
  const geoWarning = useMemo(() => {
    if (!query || query.candidates.length < 4) return null;
    const countries = new Map<string, number>();
    for (const c of query.candidates) {
      const aff = c.affiliation || "Unknown";
      countries.set(aff, (countries.get(aff) || 0) + 1);
    }
    for (const [name, count] of countries) {
      if (count / query.candidates.length > 0.75) {
        return `${Math.round((count / query.candidates.length) * 100)}% of candidates are from "${name}". Consider broadening geographic scope.`;
      }
    }
    return null;
  }, [query]);

  const toggleCompare = (uuid: string) => {
    setSelectedForCompare((prev) => {
      const next = new Set(prev);
      if (next.has(uuid)) next.delete(uuid);
      else next.add(uuid);
      return next;
    });
  };

  if (loading && !sseState.sources.size) return <LoadingSpinner message="Loading results..." />;
  if (error) return <ErrorAlert message={error} onRetry={fetchQuery} />;

  return (
    <div>
      {/* SSE source progress */}
      {loading && sseState.sources.size > 0 && (
        <SourceProgressBar
          sources={sseState.sources}
          totalSources={sseState.totalSources}
        />
      )}

      {query && (
        <>
          {/* Query header */}
          <div className="mb-6">
            <div className="flex items-start justify-between">
              <div>
                <div className="flex items-center gap-3">
                  <h1 className="text-2xl font-bold text-gray-900">Query Results</h1>
                  {(query as QueryResponse & { query_type?: string }).query_type && (
                    <QueryTypeBadge
                      queryType={(query as QueryResponse & { query_type: string }).query_type as "basic_research" | "drug_discovery" | "clinical_trial_pi" | "policy_epi"}
                      confidence={1}
                    />
                  )}
                </div>
                <p className="mt-2 text-sm text-gray-600 max-w-3xl">{query.task_description}</p>
                <div className="flex items-center space-x-4 mt-2 text-xs text-gray-500">
                  {query.population && (
                    <span className="inline-flex items-center rounded-full bg-gray-100 px-2 py-0.5 font-medium">
                      {query.population.replace("_", " ")}
                    </span>
                  )}
                  <span>K = {query.k}</span>
                  <span>{query.candidates.length} results</span>
                  <span>{new Date(query.created_at).toLocaleString()}</span>
                </div>
              </div>

              {/* Submit Feedback button */}
              <div>
                {feedbackSubmitted ? (
                  <span className="inline-flex items-center rounded-md bg-green-50 px-3 py-2 text-sm font-medium text-green-700">
                    Feedback submitted
                  </span>
                ) : (
                  <button
                    onClick={() => setShowFeedback(true)}
                    className="px-4 py-2 rounded-md bg-white border border-gray-300 text-sm font-medium text-gray-700 hover:bg-gray-50 shadow-sm transition-colors"
                  >
                    Submit Feedback
                  </button>
                )}
              </div>
            </div>
          </div>

          {/* Geographic coverage warning */}
          {geoWarning && (
            <div className="rounded-md bg-yellow-50 border border-yellow-200 p-3 mb-4">
              <p className="text-sm text-yellow-800">{geoWarning}</p>
            </div>
          )}

          {/* Weight sliders */}
          <div className="mb-4">
            <WeightSliderPanel
              weights={{}}
              exponents={exponents}
              onExponentsChange={setExponents}
              defaultExponents={{ alpha: 1, beta: 1, gamma: 1 }}
            />
          </div>

          {/* Candidate list */}
          {rankedCandidates.length === 0 ? (
            <div className="text-center py-12">
              <p className="text-gray-500">No candidates found for this query.</p>
            </div>
          ) : (
            <div className="space-y-3">
              {rankedCandidates.map((candidate) => (
                <CandidateRow
                  key={candidate.uuid}
                  candidate={candidate}
                  queryId={queryId}
                  judgment={judgments[candidate.uuid] ?? null}
                  onJudge={handleJudge}
                  isCompareSelected={selectedForCompare.has(candidate.uuid)}
                  onToggleCompare={() => toggleCompare(candidate.uuid)}
                />
              ))}
            </div>
          )}

          {/* Feedback modal */}
          {showFeedback && (
            <FeedbackModal
              queryId={queryId}
              onClose={() => setShowFeedback(false)}
              onSuccess={() => {
                setShowFeedback(false);
                setFeedbackSubmitted(true);
              }}
              querySpecialty={(query as QueryResponse & { query_type?: string }).query_type ?? "basic_research"}
              meshTerms={(query as QueryResponse & { expansion_info?: { expanded_mesh_terms?: string[] } }).expansion_info?.expanded_mesh_terms ?? []}
              candidates={rankedCandidates.map((c) => ({
                candidate_uuid: c.uuid,
                rank: c.rank,
                quality_prior_score: c.score_components?.Q ?? 0.5,
                topical_fit_score: c.score_components?.C ?? 0.5,
                recency_score: c.score_components?.R ?? 0.5,
              }))}
            />
          )}

          {/* Floating compare button */}
          {selectedForCompare.size >= 2 && (
            <div className="fixed bottom-6 right-6 z-40">
              <button
                onClick={() => setShowComparison(true)}
                className="px-5 py-3 rounded-full bg-blue-600 text-white text-sm font-medium shadow-lg hover:bg-blue-700 transition-colors"
              >
                Compare ({selectedForCompare.size})
              </button>
            </div>
          )}

          {/* Comparison modal */}
          {showComparison && (
            <CandidateComparisonModal
              candidates={rankedCandidates.filter((c) =>
                selectedForCompare.has(c.uuid)
              )}
              onClose={() => setShowComparison(false)}
            />
          )}
        </>
      )}
    </div>
  );
}
