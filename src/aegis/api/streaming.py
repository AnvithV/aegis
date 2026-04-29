"""SSE streaming for live query progress."""

from __future__ import annotations

import asyncio
import json
import logging
from collections.abc import AsyncGenerator

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

logger = logging.getLogger(__name__)

router = APIRouter()

# In-memory store for active query streams
_active_streams: dict[str, asyncio.Queue[dict | None]] = {}


def get_or_create_queue(query_id: str) -> asyncio.Queue[dict | None]:
    """Get or create an SSE queue for a query."""
    if query_id not in _active_streams:
        _active_streams[query_id] = asyncio.Queue()
    return _active_streams[query_id]


def push_event(query_id: str, event_type: str, data: dict) -> None:
    """Push an SSE event to a query's stream (non-blocking)."""
    queue = _active_streams.get(query_id)
    if queue is not None:
        try:
            queue.put_nowait({"type": event_type, "data": data})
        except asyncio.QueueFull:
            logger.warning("SSE queue full for query %s, dropping event", query_id)


def close_stream(query_id: str) -> None:
    """Signal stream completion by pushing a sentinel."""
    queue = _active_streams.get(query_id)
    if queue is not None:
        try:
            queue.put_nowait(None)
        except asyncio.QueueFull:
            pass


@router.get("/v1/queries/{query_id}/stream")
async def stream_query_progress(query_id: str) -> StreamingResponse:
    """Stream source-by-source progress as Server-Sent Events."""
    queue = get_or_create_queue(query_id)

    async def event_generator() -> AsyncGenerator[str, None]:
        try:
            while True:
                event = await asyncio.wait_for(queue.get(), timeout=300.0)
                if event is None:  # sentinel for stream end
                    yield "event: complete\ndata: {}\n\n"
                    break
                yield f"event: {event['type']}\ndata: {json.dumps(event['data'])}\n\n"
        except TimeoutError:
            yield "event: timeout\ndata: {}\n\n"
        finally:
            _active_streams.pop(query_id, None)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
    )
