"use client";

import { useState, useRef, useEffect } from "react";
import type { QueryType } from "@/types/api";

const TYPE_CONFIG: Record<QueryType, { label: string; color: string; bg: string }> = {
  drug_discovery: { label: "Drug Discovery", color: "text-purple-800", bg: "bg-purple-100" },
  clinical_trial_pi: { label: "Clinical Trial PI", color: "text-green-800", bg: "bg-green-100" },
  basic_research: { label: "Basic Research", color: "text-blue-800", bg: "bg-blue-100" },
  policy_epi: { label: "Policy / Epi", color: "text-orange-800", bg: "bg-orange-100" },
};

const ALL_TYPES: QueryType[] = ["basic_research", "drug_discovery", "clinical_trial_pi", "policy_epi"];

interface QueryTypeBadgeProps {
  queryType: QueryType;
  confidence: number;
  onOverride?: (type: QueryType) => void;
}

export default function QueryTypeBadge({ queryType, confidence, onOverride }: QueryTypeBadgeProps) {
  const [showDropdown, setShowDropdown] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) {
        setShowDropdown(false);
      }
    };
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  const config = TYPE_CONFIG[queryType];

  return (
    <div ref={ref} className="relative inline-block">
      <button
        type="button"
        onClick={() => setShowDropdown(!showDropdown)}
        className={`inline-flex items-center gap-1.5 rounded-full px-3 py-1 text-xs font-medium ${config.bg} ${config.color}`}
      >
        {config.label}
        <span className="opacity-70">{Math.round(confidence * 100)}%</span>
        <svg className="h-3 w-3 opacity-50" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
        </svg>
      </button>

      {showDropdown && (
        <div className="absolute z-10 mt-1 w-48 rounded-md bg-white shadow-lg ring-1 ring-black ring-opacity-5">
          <div className="py-1">
            {ALL_TYPES.map((t) => {
              const tc = TYPE_CONFIG[t];
              return (
                <button
                  key={t}
                  type="button"
                  onClick={() => {
                    onOverride?.(t);
                    setShowDropdown(false);
                  }}
                  className={`block w-full px-4 py-2 text-left text-sm hover:bg-gray-50 ${t === queryType ? "font-semibold" : ""}`}
                >
                  <span className={`inline-block w-2 h-2 rounded-full mr-2 ${tc.bg}`} />
                  {tc.label}
                </button>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}
