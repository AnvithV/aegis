"use client";
import { useState, useCallback } from "react";
import type { Shortlist } from "@/types/api";

export function useShortlist() {
  const [shortlists, setShortlists] = useState<Shortlist[]>([]);
  const [loading, setLoading] = useState(false);

  const fetchShortlists = useCallback(async () => {
    setLoading(true);
    try {
      const res = await fetch("/api/shortlists");
      const data = await res.json();
      setShortlists(data.shortlists || []);
    } finally {
      setLoading(false);
    }
  }, []);

  const addCandidate = useCallback(async (shortlistId: string, candidateUuid: string) => {
    await fetch(`/api/shortlists/${shortlistId}/candidates`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ candidate_uuid: candidateUuid }),
    });
  }, []);

  const createShortlist = useCallback(async (name: string, description?: string) => {
    const res = await fetch("/api/shortlists", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name, description }),
    });
    const data = await res.json();
    await fetchShortlists();
    return data.id as string;
  }, [fetchShortlists]);

  return { shortlists, loading, fetchShortlists, addCandidate, createShortlist };
}
