import { NextRequest, NextResponse } from "next/server";
import { apiFetch } from "@/lib/api-client";
import type { FeedbackRequest, FeedbackResponse } from "@/types/api";

export async function POST(
  request: NextRequest,
  { params }: { params: Promise<{ taskId: string }> }
) {
  try {
    const { taskId } = await params;
    const body: FeedbackRequest = await request.json();
    const data = await apiFetch<FeedbackResponse>(
      `/v1/feedback/tasks/${taskId}/outcomes`,
      { method: "POST", body }
    );
    return NextResponse.json(data);
  } catch (error) {
    const message = error instanceof Error ? error.message : "Internal server error";
    return NextResponse.json({ error: message }, { status: 500 });
  }
}
