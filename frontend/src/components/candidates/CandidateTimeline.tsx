"use client";

import { useState } from "react";
import type { EvidenceItem } from "@/types/api";

interface CandidateTimelineProps {
  evidenceItems: EvidenceItem[];
}

const TYPE_CATEGORIES: Record<string, string> = {
  publication: "Publications",
  pmid: "Publications",
  pmid_rcr: "Publications",
  grant: "Grants",
  trial: "Trials",
  nct: "Trials",
  patent: "Patents",
};

const TYPE_ICONS: Record<string, string> = {
  Publications: "M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253",
  Grants: "M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z",
  Trials: "M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-6 9l2 2 4-4",
  Patents: "M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z",
};

const TYPE_COLORS: Record<string, string> = {
  Publications: "bg-blue-500",
  Grants: "bg-green-500",
  Trials: "bg-purple-500",
  Patents: "bg-amber-500",
};

function getCategory(item: EvidenceItem): string {
  return TYPE_CATEGORIES[item.type] ?? "Publications";
}

export default function CandidateTimeline({ evidenceItems }: CandidateTimelineProps) {
  const [activeFilter, setActiveFilter] = useState<string>("All");

  const categories = Array.from(new Set(evidenceItems.map(getCategory))).sort();
  const filters = ["All", ...categories];

  const filtered =
    activeFilter === "All"
      ? evidenceItems
      : evidenceItems.filter((item) => getCategory(item) === activeFilter);

  // Sort by date descending
  const sorted = [...filtered].sort((a, b) => {
    if (!a.date && !b.date) return 0;
    if (!a.date) return 1;
    if (!b.date) return -1;
    return new Date(b.date).getTime() - new Date(a.date).getTime();
  });

  return (
    <div>
      {/* Filter tabs */}
      <div className="flex gap-1 mb-4 flex-wrap">
        {filters.map((filter) => {
          const count =
            filter === "All"
              ? evidenceItems.length
              : evidenceItems.filter((item) => getCategory(item) === filter).length;
          return (
            <button
              key={filter}
              onClick={() => setActiveFilter(filter)}
              className={`px-3 py-1 rounded-full text-xs font-medium transition-colors ${
                activeFilter === filter
                  ? "bg-blue-600 text-white"
                  : "bg-gray-100 text-gray-600 hover:bg-gray-200"
              }`}
            >
              {filter} ({count})
            </button>
          );
        })}
      </div>

      {/* Timeline */}
      {sorted.length === 0 ? (
        <p className="text-sm text-gray-500">No evidence items found.</p>
      ) : (
        <div className="relative">
          {/* Vertical line */}
          <div className="absolute left-4 top-0 bottom-0 w-0.5 bg-gray-200" />

          <div className="space-y-4">
            {sorted.map((item, index) => {
              const category = getCategory(item);
              const dotColor = TYPE_COLORS[category] ?? "bg-gray-400";
              const iconPath = TYPE_ICONS[category];
              return (
                <div key={index} className="relative flex items-start pl-10">
                  {/* Dot */}
                  <div
                    className={`absolute left-2.5 w-3 h-3 rounded-full ${dotColor} ring-2 ring-white`}
                  />

                  <div className="flex-1 min-w-0 bg-gray-50 rounded-lg p-3">
                    <div className="flex items-start gap-2">
                      {iconPath && (
                        <svg
                          className="h-4 w-4 text-gray-400 flex-shrink-0 mt-0.5"
                          fill="none"
                          viewBox="0 0 24 24"
                          stroke="currentColor"
                          strokeWidth={1.5}
                        >
                          <path strokeLinecap="round" strokeLinejoin="round" d={iconPath} />
                        </svg>
                      )}
                      <div className="flex-1 min-w-0">
                        <p className="text-sm text-gray-900">{item.description}</p>
                        <div className="flex items-center gap-2 mt-1 flex-wrap">
                          <span className="inline-flex items-center rounded bg-gray-200 px-1.5 py-0.5 text-xs font-medium text-gray-700">
                            {item.type}
                          </span>
                          <span className="text-xs text-gray-400 uppercase tracking-wide">
                            {item.source}
                          </span>
                          {item.date && (
                            <span className="text-xs text-gray-500">{item.date}</span>
                          )}
                          {item.score_contribution !== undefined && (
                            <span className="text-xs text-gray-500">
                              contribution {item.score_contribution.toFixed(3)}
                            </span>
                          )}
                        </div>
                        {item.url && (
                          <a
                            href={item.url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="text-xs text-blue-600 hover:text-blue-500 mt-1 inline-block"
                          >
                            View source &rarr;
                          </a>
                        )}
                      </div>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}
