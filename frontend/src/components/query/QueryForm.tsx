"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import type { Population, QueryRequest } from "@/types/api";
import PopulationSelector from "./PopulationSelector";
import KSlider from "./KSlider";
import MeshTagInput from "./MeshTagInput";

export default function QueryForm() {
  const router = useRouter();
  const [taskDescription, setTaskDescription] = useState("");
  const [population, setPopulation] = useState<Population | "auto" | "">("");
  const [k, setK] = useState(20);
  const [meshOverride, setMeshOverride] = useState<string[]>([]);
  const [cutoffStrategy, setCutoffStrategy] = useState("");
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    if (!taskDescription.trim()) {
      setError("Task description is required.");
      return;
    }

    setIsSubmitting(true);

    try {
      const body: QueryRequest = {
        task_description: taskDescription.trim(),
        k,
      };

      if (population && population !== "auto") {
        body.population = population;
      }

      if (meshOverride.length > 0) {
        body.mesh_override = meshOverride;
      }

      if (cutoffStrategy.trim()) {
        body.cutoff_strategy = cutoffStrategy.trim();
      }

      const response = await fetch("/api/queries", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });

      if (!response.ok) {
        const errData = await response.json().catch(() => ({}));
        throw new Error((errData as { error?: string }).error || `Request failed with status ${response.status}`);
      }

      const data = await response.json() as { id: string };
      router.push(`/results/${data.id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "An unexpected error occurred.");
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-6">
      {error && (
        <div className="rounded-md bg-red-50 p-4">
          <p className="text-sm text-red-700">{error}</p>
        </div>
      )}

      <div>
        <label htmlFor="task-description" className="block text-sm font-medium text-gray-700 mb-1">
          Task Description <span className="text-red-500">*</span>
        </label>
        <textarea
          id="task-description"
          rows={5}
          value={taskDescription}
          onChange={(e) => setTaskDescription(e.target.value)}
          placeholder="Describe the labeling task and the type of researcher expertise needed..."
          className="block w-full rounded-md border border-gray-300 px-3 py-2 text-sm shadow-sm placeholder:text-gray-400 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
          required
        />
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <PopulationSelector value={population} onChange={setPopulation} />
        <KSlider value={k} onChange={setK} />
      </div>

      <div>
        <button
          type="button"
          onClick={() => setShowAdvanced(!showAdvanced)}
          className="flex items-center text-sm text-gray-500 hover:text-gray-700"
        >
          <svg
            className={`h-4 w-4 mr-1 transition-transform ${showAdvanced ? "rotate-90" : ""}`}
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
          >
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
          </svg>
          Advanced Options
        </button>

        {showAdvanced && (
          <div className="mt-4 space-y-4 pl-5 border-l-2 border-gray-200">
            <MeshTagInput tags={meshOverride} onChange={setMeshOverride} />
            <div>
              <label htmlFor="cutoff-strategy" className="block text-sm font-medium text-gray-700 mb-1">
                Cutoff Strategy
              </label>
              <input
                id="cutoff-strategy"
                type="text"
                value={cutoffStrategy}
                onChange={(e) => setCutoffStrategy(e.target.value)}
                placeholder="e.g., score_threshold, elbow"
                className="block w-full rounded-md border border-gray-300 px-3 py-2 text-sm shadow-sm placeholder:text-gray-400 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
              />
              <p className="mt-1 text-xs text-gray-500">
                Optional. Determines how candidates below the quality threshold are cut.
              </p>
            </div>
          </div>
        )}
      </div>

      <div className="pt-4">
        <button
          type="submit"
          disabled={isSubmitting || !taskDescription.trim()}
          className="w-full sm:w-auto px-6 py-2.5 rounded-md bg-blue-600 text-white text-sm font-medium shadow-sm hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
        >
          {isSubmitting ? (
            <span className="flex items-center justify-center">
              <svg className="animate-spin -ml-1 mr-2 h-4 w-4 text-white" fill="none" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
              </svg>
              Submitting Query...
            </span>
          ) : (
            "Submit Query"
          )}
        </button>
      </div>
    </form>
  );
}
