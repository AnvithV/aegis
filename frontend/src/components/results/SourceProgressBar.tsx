"use client";

import type { SourceProgressEvent } from "@/types/api";

const SOURCE_NAMES = [
  "PubMed", "iCite", "NIH Reporter", "CT.gov", "OpenAlex",
  "LEIE", "ORI", "Retraction Watch", "OFAC/SAM", "USPTO",
  "EPO", "NPPES", "ABMS", "USNWR", "CMS",
];

interface SourceProgressBarProps {
  sources: Map<string, SourceProgressEvent>;
  totalSources: number;
}

function statusIcon(status?: string) {
  if (!status || status === "pending") {
    return <span className="h-4 w-4 rounded-full bg-gray-300 block" />;
  }
  if (status === "fetching") {
    return (
      <svg className="animate-spin h-4 w-4 text-blue-500" fill="none" viewBox="0 0 24 24">
        <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
        <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
      </svg>
    );
  }
  if (status === "complete") {
    return (
      <svg className="h-4 w-4 text-green-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
      </svg>
    );
  }
  // failed
  return (
    <svg className="h-4 w-4 text-red-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
    </svg>
  );
}

function tileBg(status?: string) {
  if (!status || status === "pending") return "bg-gray-50 border-gray-200";
  if (status === "fetching") return "bg-blue-50 border-blue-300 animate-pulse";
  if (status === "complete") return "bg-green-50 border-green-200";
  return "bg-red-50 border-red-200";
}

export default function SourceProgressBar({ sources, totalSources }: SourceProgressBarProps) {
  const completed = Array.from(sources.values()).filter(
    (s) => s.status === "complete" || s.status === "failed"
  ).length;
  const pct = totalSources > 0 ? (completed / totalSources) * 100 : 0;

  return (
    <div className="rounded-lg border border-gray-200 bg-white p-4 mb-6">
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-sm font-semibold text-gray-700">Source Progress</h3>
        <span className="text-xs text-gray-500">
          {completed}/{totalSources} sources complete
        </span>
      </div>

      {/* Overall progress bar */}
      <div className="w-full bg-gray-200 rounded-full h-2 mb-4">
        <div
          className="bg-blue-600 h-2 rounded-full transition-all duration-300"
          style={{ width: `${pct}%` }}
        />
      </div>

      {/* Source tiles grid */}
      <div className="grid grid-cols-5 gap-2">
        {SOURCE_NAMES.map((name) => {
          const key = name.toLowerCase().replace(/[^a-z]/g, "_");
          const evt = sources.get(key) || sources.get(name);
          const status = evt?.status;
          return (
            <div
              key={name}
              className={`rounded-md border px-2 py-1.5 flex items-center gap-1.5 ${tileBg(status)}`}
            >
              {statusIcon(status)}
              <div className="min-w-0 flex-1">
                <span className="text-xs font-medium text-gray-700 truncate block">{name}</span>
                {evt && status === "complete" && (
                  <span className="text-[10px] text-gray-400">{evt.latency_ms}ms</span>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
