"use client";

import { useState } from "react";
import type { FeedbackRequest } from "@/types/api";

interface FeedbackModalProps {
  queryId: string;
  onClose: () => void;
  onSuccess: () => void;
}

export default function FeedbackModal({ queryId, onClose, onSuccess }: FeedbackModalProps) {
  const [fleissKappa, setFleissKappa] = useState("");
  const [acceptRate, setAcceptRate] = useState("");
  const [consensusRate, setConsensusRate] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const validateRange = (value: string, label: string): number => {
    const num = parseFloat(value);
    if (isNaN(num) || num < 0 || num > 1) {
      throw new Error(`${label} must be a number between 0 and 1.`);
    }
    return num;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    try {
      const body: FeedbackRequest = {
        fleiss_kappa: validateRange(fleissKappa, "Fleiss Kappa"),
        accept_rate: validateRange(acceptRate, "Accept Rate"),
        consensus_rate: validateRange(consensusRate, "Consensus Rate"),
      };

      setIsSubmitting(true);

      const response = await fetch(`/api/feedback/tasks/${queryId}/outcomes`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });

      if (!response.ok) {
        const errData = await response.json().catch(() => ({}));
        throw new Error((errData as { error?: string }).error || `Request failed with status ${response.status}`);
      }

      onSuccess();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to submit feedback.");
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg shadow-xl max-w-md w-full mx-4 p-6">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-semibold text-gray-900">Submit Feedback</h3>
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

        <p className="text-sm text-gray-600 mb-4">
          Submit downstream task quality feedback for this query.
        </p>

        {error && (
          <div className="rounded-md bg-red-50 p-3 mb-4">
            <p className="text-sm text-red-700">{error}</p>
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label htmlFor="fleiss-kappa" className="block text-sm font-medium text-gray-700 mb-1">
              Fleiss Kappa (0-1)
            </label>
            <input
              id="fleiss-kappa"
              type="number"
              step="0.01"
              min="0"
              max="1"
              value={fleissKappa}
              onChange={(e) => setFleissKappa(e.target.value)}
              placeholder="0.00"
              className="block w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
              required
            />
            <p className="mt-1 text-xs text-gray-500">Inter-rater agreement on the label set.</p>
          </div>

          <div>
            <label htmlFor="accept-rate" className="block text-sm font-medium text-gray-700 mb-1">
              Accept Rate (0-1)
            </label>
            <input
              id="accept-rate"
              type="number"
              step="0.01"
              min="0"
              max="1"
              value={acceptRate}
              onChange={(e) => setAcceptRate(e.target.value)}
              placeholder="0.00"
              className="block w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
              required
            />
            <p className="mt-1 text-xs text-gray-500">Fraction of labels accepted by the customer.</p>
          </div>

          <div>
            <label htmlFor="consensus-rate" className="block text-sm font-medium text-gray-700 mb-1">
              Consensus Rate (0-1)
            </label>
            <input
              id="consensus-rate"
              type="number"
              step="0.01"
              min="0"
              max="1"
              value={consensusRate}
              onChange={(e) => setConsensusRate(e.target.value)}
              placeholder="0.00"
              className="block w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
              required
            />
            <p className="mt-1 text-xs text-gray-500">Post-hoc consensus rate.</p>
          </div>

          <div className="flex space-x-3 pt-2">
            <button
              type="submit"
              disabled={isSubmitting}
              className="flex-1 px-4 py-2 rounded-md bg-blue-600 text-white text-sm font-medium hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              {isSubmitting ? "Submitting..." : "Submit Feedback"}
            </button>
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 rounded-md border border-gray-300 text-gray-700 text-sm font-medium hover:bg-gray-50 transition-colors"
            >
              Cancel
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
