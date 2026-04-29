"use client";

import Link from "next/link";
import type { QuerySummary } from "@/types/api";

interface QueryTableProps {
  queries: QuerySummary[];
  onRerun?: (query: QuerySummary) => void;
}

const POPULATION_COLORS: Record<string, string> = {
  translational: "bg-blue-100 text-blue-800",
  drug_discovery: "bg-purple-100 text-purple-800",
  clinician: "bg-green-100 text-green-800",
};

export default function QueryTable({ queries, onRerun }: QueryTableProps) {
  if (queries.length === 0) {
    return (
      <div className="text-center py-12">
        <p className="text-gray-500">No queries found. Submit your first query to get started.</p>
        <Link
          href="/"
          className="mt-4 inline-flex items-center px-4 py-2 rounded-md bg-blue-600 text-white text-sm font-medium hover:bg-blue-700 transition-colors"
        >
          New Query
        </Link>
      </div>
    );
  }

  return (
    <div className="overflow-x-auto">
      <table className="min-w-full divide-y divide-gray-200">
        <thead className="bg-gray-50">
          <tr>
            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
              Timestamp
            </th>
            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
              Task Description
            </th>
            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
              Type
            </th>
            <th className="px-6 py-3 text-center text-xs font-medium text-gray-500 uppercase tracking-wider">
              K
            </th>
            <th className="px-6 py-3 text-center text-xs font-medium text-gray-500 uppercase tracking-wider">
              Results
            </th>
            <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
              Actions
            </th>
          </tr>
        </thead>
        <tbody className="bg-white divide-y divide-gray-200">
          {queries.map((query) => (
            <tr key={query.id} className="hover:bg-gray-50 transition-colors">
              <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                {new Date(query.created_at).toLocaleString()}
              </td>
              <td className="px-6 py-4 text-sm text-gray-900 max-w-xs truncate" title={query.task_description}>
                {query.task_description}
              </td>
              <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                {query.population ? (
                  <span className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ${POPULATION_COLORS[query.population] ?? "bg-gray-100 text-gray-700"}`}>
                    {query.population.replace(/_/g, " ")}
                  </span>
                ) : (
                  <span className="text-gray-400">--</span>
                )}
              </td>
              <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500 text-center">
                {query.k}
              </td>
              <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500 text-center">
                {query.result_count}
              </td>
              <td className="px-6 py-4 whitespace-nowrap text-sm text-right space-x-2">
                <Link
                  href={`/results/${query.id}`}
                  className="text-blue-600 hover:text-blue-800 font-medium"
                >
                  View
                </Link>
                {onRerun && (
                  <button
                    onClick={() => onRerun(query)}
                    className="text-green-600 hover:text-green-800 font-medium"
                  >
                    Re-run
                  </button>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
