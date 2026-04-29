"use client";

import { useState } from "react";

interface WeightSliderPanelProps {
  weights: Record<string, number>;
  exponents: Record<string, number>;
  onExponentsChange: (exponents: Record<string, number>) => void;
  defaultExponents?: Record<string, number>;
}

const SLIDER_CONFIG = [
  { key: "alpha", label: "Quality", min: 0, max: 2, step: 0.05 },
  { key: "beta", label: "Topical Fit", min: 0, max: 2, step: 0.05 },
  { key: "gamma", label: "Recency", min: 0, max: 2, step: 0.05 },
];

const F_LABELS: Record<string, string> = {
  f1_rcr: "F1 RCR",
  f2_funding: "F2 Funding",
  f3_leadership: "F3 Leadership",
  f4_apex: "F4 Apex",
  f5_translational: "F5 Translational",
  f6_lineage: "F6 Lineage",
  f7_clinician: "F7 Clinician",
};

export default function WeightSliderPanel({ weights, exponents, onExponentsChange, defaultExponents }: WeightSliderPanelProps) {
  const [collapsed, setCollapsed] = useState(true);

  return (
    <div className="rounded-md border border-gray-200 bg-white">
      <button
        type="button"
        onClick={() => setCollapsed(!collapsed)}
        className="flex w-full items-center justify-between px-4 py-3 text-sm font-medium text-gray-700 hover:bg-gray-50"
      >
        <span>Weight Configuration</span>
        <svg
          className={`h-4 w-4 transition-transform ${collapsed ? "" : "rotate-180"}`}
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
        >
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
        </svg>
      </button>

      {!collapsed && (
        <div className="border-t border-gray-200 px-4 py-4 space-y-5">
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <h4 className="text-xs font-semibold text-gray-500 uppercase tracking-wider">Exponents</h4>
              {defaultExponents && (
                <button
                  onClick={() => onExponentsChange(defaultExponents)}
                  className="text-xs text-slate-400 hover:text-slate-200 underline"
                >
                  Reset to trained
                </button>
              )}
            </div>
            {SLIDER_CONFIG.map(({ key, label, min, max, step }) => (
              <div key={key}>
                <div className="flex justify-between text-sm mb-1">
                  <span className="text-gray-600">{label}</span>
                  <span className="font-mono text-gray-800">{(exponents[key] ?? 1).toFixed(2)}</span>
                </div>
                <input
                  type="range"
                  min={min}
                  max={max}
                  step={step}
                  value={exponents[key] ?? 1}
                  onChange={(e) =>
                    onExponentsChange({ ...exponents, [key]: parseFloat(e.target.value) })
                  }
                  className="w-full h-1.5 bg-gray-200 rounded-lg appearance-none cursor-pointer accent-blue-600"
                />
              </div>
            ))}
          </div>

          <div className="space-y-2">
            <h4 className="text-xs font-semibold text-gray-500 uppercase tracking-wider">F1-F7 Weights (read-only)</h4>
            <div className="grid grid-cols-2 gap-2">
              {Object.entries(F_LABELS).map(([key, label]) => {
                const val = weights[key];
                if (val === undefined) return null;
                return (
                  <div key={key} className="flex justify-between text-sm bg-gray-50 rounded px-2 py-1">
                    <span className="text-gray-600">{label}</span>
                    <span className="font-mono text-gray-800">{val.toFixed(3)}</span>
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
