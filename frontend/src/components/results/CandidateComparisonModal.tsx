"use client";

import type { CandidateResult } from "@/types/api";
import {
  RadarChart,
  Radar,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
  ResponsiveContainer,
  Legend,
} from "recharts";

const COLORS = ["#3b82f6", "#ef4444", "#10b981", "#f59e0b"];

interface CandidateComparisonModalProps {
  candidates: CandidateResult[];
  onClose: () => void;
}

export default function CandidateComparisonModal({
  candidates,
  onClose,
}: CandidateComparisonModalProps) {
  const radarMetrics = ["Q", "C", "R", "I"] as const;
  const radarData = radarMetrics.map((metric) => {
    const entry: Record<string, string | number> = { metric };
    candidates.forEach((c, i) => {
      entry[`c${i}`] = c.score_components[metric] * 100;
    });
    return entry;
  });

  const handleExport = () => {
    const lines = ["Name,Rank,Score,Q,C,R,I,Affiliation"];
    candidates.forEach((c) => {
      lines.push(
        `"${c.name}",${c.rank},${c.score.toFixed(3)},${c.score_components.Q.toFixed(3)},${c.score_components.C.toFixed(3)},${c.score_components.R.toFixed(3)},${c.score_components.I.toFixed(3)},"${c.affiliation}"`
      );
    });
    const blob = new Blob([lines.join("\n")], { type: "text/csv" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "comparison.csv";
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-lg shadow-xl max-w-6xl w-full max-h-[90vh] overflow-y-auto">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200">
          <h3 className="text-lg font-semibold text-gray-900">
            Candidate Comparison ({candidates.length})
          </h3>
          <div className="flex items-center gap-3">
            <button
              onClick={handleExport}
              className="px-3 py-1.5 rounded-md border border-gray-300 text-sm font-medium text-gray-700 hover:bg-gray-50"
            >
              Export Comparison
            </button>
            <button
              onClick={onClose}
              className="text-gray-400 hover:text-gray-600"
              aria-label="Close"
            >
              <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>
        </div>

        {/* Radar chart */}
        <div className="px-6 py-4 border-b border-gray-200">
          <h4 className="text-sm font-semibold text-gray-700 mb-2">Score Components Overlay</h4>
          <ResponsiveContainer width="100%" height={300}>
            <RadarChart data={radarData}>
              <PolarGrid />
              <PolarAngleAxis dataKey="metric" />
              <PolarRadiusAxis angle={30} domain={[0, 100]} />
              {candidates.map((c, i) => (
                <Radar
                  key={c.uuid}
                  name={c.name}
                  dataKey={`c${i}`}
                  stroke={COLORS[i % COLORS.length]}
                  fill={COLORS[i % COLORS.length]}
                  fillOpacity={0.15}
                />
              ))}
              <Legend />
            </RadarChart>
          </ResponsiveContainer>
        </div>

        {/* Side-by-side columns */}
        <div className={`grid gap-4 p-6 grid-cols-${Math.min(candidates.length, 4)}`} style={{ gridTemplateColumns: `repeat(${Math.min(candidates.length, 4)}, minmax(0, 1fr))` }}>
          {candidates.map((c, i) => (
            <div key={c.uuid} className="border border-gray-200 rounded-lg p-4">
              {/* Name & rank */}
              <div className="flex items-center gap-2 mb-3">
                <div
                  className="w-8 h-8 rounded-full flex items-center justify-center text-white text-xs font-bold"
                  style={{ backgroundColor: COLORS[i % COLORS.length] }}
                >
                  #{c.rank}
                </div>
                <div>
                  <h5 className="text-sm font-semibold text-gray-900">{c.name}</h5>
                  <p className="text-xs text-gray-500">{c.affiliation}</p>
                </div>
              </div>

              {/* Composite score */}
              <div className="mb-3">
                <span className="text-xs text-gray-500">Composite Score</span>
                <p className="text-2xl font-bold text-gray-900">
                  {(c.score * 100).toFixed(1)}
                </p>
              </div>

              {/* Q/C/R/I bars */}
              <div className="space-y-2 mb-3">
                {(["Q", "C", "R", "I"] as const).map((key) => (
                  <div key={key}>
                    <div className="flex justify-between text-xs mb-0.5">
                      <span className="text-gray-500">{key}</span>
                      <span className="font-mono">{(c.score_components[key] * 100).toFixed(1)}</span>
                    </div>
                    <div className="w-full bg-gray-200 rounded-full h-1.5">
                      <div
                        className="bg-blue-500 h-1.5 rounded-full"
                        style={{ width: `${c.score_components[key] * 100}%`, backgroundColor: COLORS[i % COLORS.length] }}
                      />
                    </div>
                  </div>
                ))}
              </div>

              {/* F1-F7 scores */}
              {c.score_components.f1_rcr !== undefined && (
                <div className="mb-3">
                  <h6 className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-1">F1-F7</h6>
                  <div className="grid grid-cols-2 gap-1 text-xs">
                    {[
                      { k: "f1_rcr", l: "F1" },
                      { k: "f2_funding", l: "F2" },
                      { k: "f3_leadership", l: "F3" },
                      { k: "f4_apex", l: "F4" },
                      { k: "f5_translational", l: "F5" },
                      { k: "f6_lineage", l: "F6" },
                      { k: "f7_clinician", l: "F7" },
                    ].map(({ k, l }) => {
                      const v = c.score_components[k as keyof typeof c.score_components];
                      if (v === undefined) return null;
                      return (
                        <div key={k} className="flex justify-between bg-gray-50 rounded px-1.5 py-0.5">
                          <span className="text-gray-500">{l}</span>
                          <span className="font-mono">{(v as number).toFixed(2)}</span>
                        </div>
                      );
                    })}
                  </div>
                </div>
              )}

              {/* Counts */}
              <div className="grid grid-cols-2 gap-1 text-xs mb-3">
                <div className="bg-gray-50 rounded px-2 py-1">
                  <span className="text-gray-500">Publications</span>
                  <span className="ml-1 font-medium">{c.top_artifacts.filter((a) => a.type === "pmid").length}</span>
                </div>
                <div className="bg-gray-50 rounded px-2 py-1">
                  <span className="text-gray-500">Grants</span>
                  <span className="ml-1 font-medium">{c.top_artifacts.filter((a) => a.type === "grant").length}</span>
                </div>
                <div className="bg-gray-50 rounded px-2 py-1">
                  <span className="text-gray-500">Trials</span>
                  <span className="ml-1 font-medium">{c.top_artifacts.filter((a) => a.type === "nct").length}</span>
                </div>
                <div className="bg-gray-50 rounded px-2 py-1">
                  <span className="text-gray-500">Patents</span>
                  <span className="ml-1 font-medium">{c.top_artifacts.filter((a) => a.type === "patent").length}</span>
                </div>
              </div>

              {/* Integrity */}
              <div className="flex items-center gap-1 text-xs">
                {c.integrity_disclosures.length === 0 ? (
                  <>
                    <svg className="h-4 w-4 text-green-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                    </svg>
                    <span className="text-green-700">Clean</span>
                  </>
                ) : (
                  <>
                    <svg className="h-4 w-4 text-red-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                    </svg>
                    <span className="text-red-700">{c.integrity_disclosures.length} flag(s)</span>
                  </>
                )}
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
