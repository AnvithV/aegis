"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import type { Shortlist } from "@/types/api";
import LoadingSpinner from "@/components/LoadingSpinner";
import ErrorAlert from "@/components/ErrorAlert";

export default function ShortlistsPage() {
  const [shortlists, setShortlists] = useState<Shortlist[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showCreate, setShowCreate] = useState(false);
  const [newName, setNewName] = useState("");
  const [newDescription, setNewDescription] = useState("");
  const [creating, setCreating] = useState(false);

  const fetchShortlists = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await fetch("/api/shortlists");
      if (!response.ok) {
        throw new Error(`Failed to load shortlists: ${response.status}`);
      }
      const data = await response.json();
      setShortlists(Array.isArray(data) ? data : data.shortlists ?? []);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load shortlists.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchShortlists();
  }, [fetchShortlists]);

  const handleCreate = async () => {
    if (!newName.trim()) return;
    setCreating(true);
    try {
      const response = await fetch("/api/shortlists", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name: newName.trim(), description: newDescription.trim() || null }),
      });
      if (response.ok) {
        setNewName("");
        setNewDescription("");
        setShowCreate(false);
        fetchShortlists();
      }
    } finally {
      setCreating(false);
    }
  };

  const handleDelete = async (id: string) => {
    try {
      await fetch(`/api/shortlists/${id}`, { method: "DELETE" });
      fetchShortlists();
    } catch {
      // silently fail
    }
  };

  if (loading) return <LoadingSpinner message="Loading shortlists..." />;
  if (error) return <ErrorAlert message={error} onRetry={fetchShortlists} />;

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Shortlists</h1>
          <p className="mt-1 text-sm text-gray-600">Organize candidates into curated shortlists.</p>
        </div>
        <button
          onClick={() => setShowCreate(!showCreate)}
          className="px-4 py-2 rounded-md bg-blue-600 text-white text-sm font-medium hover:bg-blue-700 transition-colors"
        >
          Create New Shortlist
        </button>
      </div>

      {/* Create form */}
      {showCreate && (
        <div className="bg-white border border-gray-200 rounded-lg p-6 mb-6">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">New Shortlist</h2>
          <div className="space-y-3">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Name</label>
              <input
                type="text"
                value={newName}
                onChange={(e) => setNewName(e.target.value)}
                className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
                placeholder="e.g., KRAS G12C Top Candidates"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Description (optional)</label>
              <input
                type="text"
                value={newDescription}
                onChange={(e) => setNewDescription(e.target.value)}
                className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
                placeholder="Brief description..."
              />
            </div>
            <div className="flex gap-2">
              <button
                onClick={handleCreate}
                disabled={creating || !newName.trim()}
                className="px-4 py-2 rounded-md bg-blue-600 text-white text-sm font-medium hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              >
                {creating ? "Creating..." : "Create"}
              </button>
              <button
                onClick={() => {
                  setShowCreate(false);
                  setNewName("");
                  setNewDescription("");
                }}
                className="px-4 py-2 rounded-md bg-gray-200 text-gray-700 text-sm font-medium hover:bg-gray-300 transition-colors"
              >
                Cancel
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Shortlists list */}
      {shortlists.length === 0 ? (
        <div className="text-center py-12 bg-white rounded-lg border border-gray-200">
          <p className="text-gray-500">No shortlists yet. Create one to get started.</p>
        </div>
      ) : (
        <div className="space-y-3">
          {shortlists.map((sl) => (
            <div
              key={sl.id}
              className="bg-white border border-gray-200 rounded-lg p-4 hover:bg-gray-50 transition-colors"
            >
              <div className="flex items-center justify-between">
                <Link href={`/shortlists/${sl.id}`} className="flex-1 min-w-0">
                  <h3 className="text-sm font-semibold text-gray-900">{sl.name}</h3>
                  {sl.description && (
                    <p className="text-sm text-gray-500 mt-0.5">{sl.description}</p>
                  )}
                  <div className="flex items-center gap-3 mt-1 text-xs text-gray-400">
                    <span>{sl.member_count ?? 0} candidates</span>
                    <span>Created by {sl.created_by}</span>
                    <span>{new Date(sl.created_at).toLocaleDateString()}</span>
                  </div>
                </Link>
                <button
                  onClick={(e) => {
                    e.preventDefault();
                    handleDelete(sl.id);
                  }}
                  className="ml-4 px-3 py-1 rounded-md text-xs text-red-600 hover:bg-red-50 transition-colors"
                >
                  Delete
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
