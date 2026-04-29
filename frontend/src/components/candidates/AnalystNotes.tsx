"use client";

import { useState } from "react";
import type { CandidateNote } from "@/types/api";

interface AnalystNotesProps {
  candidateUuid: string;
  notes: CandidateNote[];
  onNotesChange: () => void;
}

export default function AnalystNotes({ candidateUuid, notes, onNotesChange }: AnalystNotesProps) {
  const [newNote, setNewNote] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editContent, setEditContent] = useState("");

  const handleSubmit = async () => {
    if (!newNote.trim()) return;
    setSubmitting(true);
    try {
      const response = await fetch(`/api/candidates/${candidateUuid}/notes`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ content: newNote.trim(), author: "analyst" }),
      });
      if (response.ok) {
        setNewNote("");
        onNotesChange();
      }
    } finally {
      setSubmitting(false);
    }
  };

  const handleDelete = async (noteId: string) => {
    try {
      await fetch(`/api/candidates/${candidateUuid}/notes`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ action: "delete", note_id: noteId }),
      });
      onNotesChange();
    } catch {
      // silently fail
    }
  };

  const handleEdit = async (noteId: string) => {
    if (!editContent.trim()) return;
    try {
      await fetch(`/api/candidates/${candidateUuid}/notes`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ action: "update", note_id: noteId, content: editContent.trim() }),
      });
      setEditingId(null);
      setEditContent("");
      onNotesChange();
    } catch {
      // silently fail
    }
  };

  return (
    <div>
      {/* Existing notes */}
      {notes.length === 0 ? (
        <p className="text-sm text-gray-500 mb-4">No notes yet.</p>
      ) : (
        <div className="space-y-3 mb-4">
          {notes.map((note) => (
            <div key={note.id} className="bg-gray-50 rounded-lg p-3">
              {editingId === note.id ? (
                <div>
                  <textarea
                    value={editContent}
                    onChange={(e) => setEditContent(e.target.value)}
                    className="w-full rounded-md border border-gray-300 p-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
                    rows={3}
                  />
                  <div className="flex gap-2 mt-2">
                    <button
                      onClick={() => handleEdit(note.id)}
                      className="px-3 py-1 rounded-md bg-blue-600 text-white text-xs font-medium hover:bg-blue-700 transition-colors"
                    >
                      Save
                    </button>
                    <button
                      onClick={() => {
                        setEditingId(null);
                        setEditContent("");
                      }}
                      className="px-3 py-1 rounded-md bg-gray-200 text-gray-700 text-xs font-medium hover:bg-gray-300 transition-colors"
                    >
                      Cancel
                    </button>
                  </div>
                </div>
              ) : (
                <div>
                  <div className="flex items-center justify-between mb-1">
                    <div className="flex items-center gap-2">
                      <span className="text-xs font-medium text-gray-700">{note.author}</span>
                      <span className="text-xs text-gray-400">
                        {new Date(note.created_at).toLocaleString()}
                      </span>
                    </div>
                    <div className="flex gap-1">
                      <button
                        onClick={() => {
                          setEditingId(note.id);
                          setEditContent(note.content);
                        }}
                        className="px-2 py-0.5 rounded text-xs text-gray-500 hover:text-blue-600 hover:bg-blue-50 transition-colors"
                      >
                        Edit
                      </button>
                      <button
                        onClick={() => handleDelete(note.id)}
                        className="px-2 py-0.5 rounded text-xs text-gray-500 hover:text-red-600 hover:bg-red-50 transition-colors"
                      >
                        Delete
                      </button>
                    </div>
                  </div>
                  <p className="text-sm text-gray-800 whitespace-pre-wrap">{note.content}</p>
                </div>
              )}
            </div>
          ))}
        </div>
      )}

      {/* Add new note */}
      <div className="border-t border-gray-200 pt-4">
        <textarea
          value={newNote}
          onChange={(e) => setNewNote(e.target.value)}
          placeholder="Add a note..."
          className="w-full rounded-md border border-gray-300 p-3 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
          rows={3}
        />
        <div className="mt-2 flex justify-end">
          <button
            onClick={handleSubmit}
            disabled={submitting || !newNote.trim()}
            className="px-4 py-2 rounded-md bg-blue-600 text-white text-sm font-medium hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            {submitting ? "Saving..." : "Add Note"}
          </button>
        </div>
      </div>
    </div>
  );
}
