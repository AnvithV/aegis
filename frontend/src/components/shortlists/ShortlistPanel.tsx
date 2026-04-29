"use client";

import { useCallback, useEffect, useState } from "react";
import type { Shortlist } from "@/types/api";

interface ShortlistPanelProps {
  candidateUuid: string;
  candidateName: string;
}

export default function ShortlistPanel({ candidateUuid, candidateName }: ShortlistPanelProps) {
  const [shortlists, setShortlists] = useState<Shortlist[]>([]);
  const [selectedId, setSelectedId] = useState("");
  const [newName, setNewName] = useState("");
  const [showCreate, setShowCreate] = useState(false);
  const [adding, setAdding] = useState(false);

  const fetchShortlists = useCallback(async () => {
    try {
      const response = await fetch("/api/shortlists");
      if (response.ok) {
        const data = await response.json();
        setShortlists(Array.isArray(data) ? data : data.shortlists ?? []);
      }
    } catch {
      // silently fail
    }
  }, []);

  useEffect(() => {
    fetchShortlists();
  }, [fetchShortlists]);

  const handleAdd = async () => {
    const targetId = selectedId;
    if (!targetId) return;
    setAdding(true);
    try {
      await fetch(`/api/shortlists/${targetId}/candidates`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          candidate_uuid: candidateUuid,
          candidate_name: candidateName,
        }),
      });
      fetchShortlists();
    } finally {
      setAdding(false);
    }
  };

  const handleCreateAndAdd = async () => {
    if (!newName.trim()) return;
    setAdding(true);
    try {
      const createResponse = await fetch("/api/shortlists", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name: newName.trim() }),
      });
      if (createResponse.ok) {
        const created = await createResponse.json();
        const newId = created.id;
        if (newId) {
          await fetch(`/api/shortlists/${newId}/candidates`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              candidate_uuid: candidateUuid,
              candidate_name: candidateName,
            }),
          });
        }
        setNewName("");
        setShowCreate(false);
        fetchShortlists();
      }
    } finally {
      setAdding(false);
    }
  };

  return (
    <div className="bg-gray-50 border border-gray-200 rounded-lg p-4">
      <h4 className="text-sm font-semibold text-gray-900 mb-3">Add to Shortlist</h4>

      {shortlists.length > 0 && (
        <div className="flex gap-2 mb-3">
          <select
            value={selectedId}
            onChange={(e) => setSelectedId(e.target.value)}
            className="flex-1 rounded-md border border-gray-300 px-2 py-1.5 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
          >
            <option value="">Select shortlist...</option>
            {shortlists.map((sl) => (
              <option key={sl.id} value={sl.id}>
                {sl.name} ({sl.member_count ?? 0})
              </option>
            ))}
          </select>
          <button
            onClick={handleAdd}
            disabled={adding || !selectedId}
            className="px-3 py-1.5 rounded-md bg-blue-600 text-white text-xs font-medium hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            Add
          </button>
        </div>
      )}

      {showCreate ? (
        <div className="flex gap-2">
          <input
            type="text"
            value={newName}
            onChange={(e) => setNewName(e.target.value)}
            placeholder="New shortlist name..."
            className="flex-1 rounded-md border border-gray-300 px-2 py-1.5 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
          />
          <button
            onClick={handleCreateAndAdd}
            disabled={adding || !newName.trim()}
            className="px-3 py-1.5 rounded-md bg-green-600 text-white text-xs font-medium hover:bg-green-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            Create & Add
          </button>
          <button
            onClick={() => {
              setShowCreate(false);
              setNewName("");
            }}
            className="px-2 py-1.5 rounded-md text-xs text-gray-500 hover:bg-gray-200 transition-colors"
          >
            Cancel
          </button>
        </div>
      ) : (
        <button
          onClick={() => setShowCreate(true)}
          className="text-xs text-blue-600 hover:text-blue-800"
        >
          + Create new shortlist
        </button>
      )}
    </div>
  );
}
