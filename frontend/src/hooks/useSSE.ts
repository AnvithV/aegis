"use client";
import { useEffect, useRef, useState } from "react";
import type { SourceProgressEvent } from "@/types/api";

interface UseSSEOptions {
  queryId: string;
  enabled: boolean;
}

interface SSEState {
  sources: Map<string, SourceProgressEvent>;
  completedCount: number;
  totalSources: number;
  isComplete: boolean;
  error: string | null;
}

export function useSSE({ queryId, enabled }: UseSSEOptions): SSEState {
  const [state, setState] = useState<SSEState>({
    sources: new Map(),
    completedCount: 0,
    totalSources: 15,
    isComplete: false,
    error: null,
  });
  const eventSourceRef = useRef<EventSource | null>(null);

  useEffect(() => {
    if (!enabled || !queryId) return;

    const es = new EventSource(`/api/queries/${queryId}/stream`);
    eventSourceRef.current = es;

    es.addEventListener("source_progress", (e) => {
      const data: SourceProgressEvent = JSON.parse(e.data);
      setState((prev) => {
        const newSources = new Map(prev.sources);
        newSources.set(data.source_name, data);
        const completed = Array.from(newSources.values()).filter(
          (s) => s.status === "complete" || s.status === "failed"
        ).length;
        return { ...prev, sources: newSources, completedCount: completed };
      });
    });

    es.addEventListener("complete", () => {
      setState((prev) => ({ ...prev, isComplete: true }));
      es.close();
    });

    es.onerror = () => {
      setState((prev) => ({ ...prev, error: "Connection lost", isComplete: true }));
      es.close();
    };

    return () => {
      es.close();
      eventSourceRef.current = null;
    };
  }, [queryId, enabled]);

  return state;
}
