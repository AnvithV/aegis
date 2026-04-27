"use client";

import type { Population } from "@/types/api";

interface PopulationSelectorProps {
  value: Population | "auto" | "";
  onChange: (value: Population | "auto" | "") => void;
}

const POPULATIONS: { value: Population | "auto"; label: string }[] = [
  { value: "auto", label: "Auto-detect" },
  { value: "translational", label: "Translational" },
  { value: "drug_discovery", label: "Drug Discovery" },
  { value: "clinician", label: "Clinician" },
];

export default function PopulationSelector({ value, onChange }: PopulationSelectorProps) {
  return (
    <div>
      <label htmlFor="population" className="block text-sm font-medium text-gray-700 mb-1">
        Population
      </label>
      <select
        id="population"
        value={value}
        onChange={(e) => onChange(e.target.value as Population | "auto" | "")}
        className="block w-full rounded-md border border-gray-300 bg-white px-3 py-2 text-sm shadow-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
      >
        <option value="">-- Select (optional) --</option>
        {POPULATIONS.map((pop) => (
          <option key={pop.value} value={pop.value}>
            {pop.label}
          </option>
        ))}
      </select>
      <p className="mt-1 text-xs text-gray-500">
        Leave blank or select Auto-detect to let the system choose.
      </p>
    </div>
  );
}
