"use client";

import type { CandidateResult } from "@/types/api";

interface QueryDiffProps {
  oldResults: CandidateResult[];
  newResults: CandidateResult[];
}

interface DiffEntry {
  name: string;
  uuid: string;
  oldRank: number | null;
  newRank: number | null;
  oldScore: number | null;
  newScore: number | null;
  change: "up" | "down" | "new" | "gone" | "same";
}

export default function QueryDiff({ oldResults, newResults }: QueryDiffProps) {
  const oldMap = new Map(oldResults.map((c) => [c.uuid, c]));
  const newMap = new Map(newResults.map((c) => [c.uuid, c]));

  const entries: DiffEntry[] = [];

  // Candidates in new results
  for (const c of newResults) {
    const old = oldMap.get(c.uuid);
    if (!old) {
      entries.push({
        name: c.name,
        uuid: c.uuid,
        oldRank: null,
        newRank: c.rank,
        oldScore: null,
        newScore: c.score,
        change: "new",
      });
    } else {
      const rankDelta = old.rank - c.rank; // positive = moved up
      entries.push({
        name: c.name,
        uuid: c.uuid,
        oldRank: old.rank,
        newRank: c.rank,
        oldScore: old.score,
        newScore: c.score,
        change: rankDelta > 0 ? "up" : rankDelta < 0 ? "down" : "same",
      });
    }
  }

  // Candidates that disappeared
  for (const c of oldResults) {
    if (!newMap.has(c.uuid)) {
      entries.push({
        name: c.name,
        uuid: c.uuid,
        oldRank: c.rank,
        newRank: null,
        oldScore: c.score,
        newScore: null,
        change: "gone",
      });
    }
  }

  // Sort by new rank, with "gone" entries at the end
  entries.sort((a, b) => {
    if (a.newRank === null && b.newRank === null) return 0;
    if (a.newRank === null) return 1;
    if (b.newRank === null) return -1;
    return a.newRank - b.newRank;
  });

  const changeStyles: Record<string, { badge: string; text: string; label: string }> = {
    up: { badge: "bg-green-100 text-green-800", text: "text-green-600", label: "Up" },
    down: { badge: "bg-red-100 text-red-800", text: "text-red-600", label: "Down" },
    new: { badge: "bg-blue-100 text-blue-800", text: "text-blue-600", label: "New" },
    gone: { badge: "bg-gray-100 text-gray-500", text: "text-gray-400", label: "Gone" },
    same: { badge: "bg-gray-50 text-gray-500", text: "text-gray-500", label: "--" },
  };

  return (
    <div className="overflow-x-auto">
      <table className="min-w-full divide-y divide-gray-200">
        <thead className="bg-gray-50">
          <tr>
            <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Rank</th>
            <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Name</th>
            <th className="px-4 py-3 text-center text-xs font-medium text-gray-500 uppercase">Old Score</th>
            <th className="px-4 py-3 text-center text-xs font-medium text-gray-500 uppercase">New Score</th>
            <th className="px-4 py-3 text-center text-xs font-medium text-gray-500 uppercase">Change</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-200">
          {entries.map((entry) => {
            const style = changeStyles[entry.change];
            return (
              <tr key={entry.uuid} className={entry.change === "gone" ? "opacity-60" : ""}>
                <td className="px-4 py-3 text-sm text-gray-900">
                  {entry.change === "gone" ? (
                    <span className="line-through text-gray-400">#{entry.oldRank}</span>
                  ) : (
                    <span>#{entry.newRank}</span>
                  )}
                  {entry.oldRank !== null && entry.newRank !== null && entry.oldRank !== entry.newRank && (
                    <span className="text-xs text-gray-400 ml-1">(was #{entry.oldRank})</span>
                  )}
                </td>
                <td className={`px-4 py-3 text-sm ${entry.change === "gone" ? "line-through text-gray-400" : "text-gray-900"}`}>
                  {entry.name}
                </td>
                <td className="px-4 py-3 text-sm text-center text-gray-500">
                  {entry.oldScore !== null ? entry.oldScore.toFixed(4) : "--"}
                </td>
                <td className="px-4 py-3 text-sm text-center text-gray-900 font-medium">
                  {entry.newScore !== null ? entry.newScore.toFixed(4) : "--"}
                </td>
                <td className="px-4 py-3 text-sm text-center">
                  <span className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-medium ${style.badge}`}>
                    {entry.change === "up" && (
                      <svg className="h-3 w-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                        <path strokeLinecap="round" strokeLinejoin="round" d="M5 15l7-7 7 7" />
                      </svg>
                    )}
                    {entry.change === "down" && (
                      <svg className="h-3 w-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                        <path strokeLinecap="round" strokeLinejoin="round" d="M19 9l-7 7-7-7" />
                      </svg>
                    )}
                    {style.label}
                  </span>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
