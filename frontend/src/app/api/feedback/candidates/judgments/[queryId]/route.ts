import { NextRequest, NextResponse } from "next/server";
import { apiFetch } from "@/lib/api-client";

export async function GET(
  _request: NextRequest,
  { params }: { params: Promise<{ queryId: string }> }
) {
  try {
    const { queryId } = await params;
    const data = await apiFetch<Record<string, unknown>>(
      `/v1/feedback/candidates/judgments/${queryId}`
    );
    return NextResponse.json(data);
  } catch (error) {
    const message =
      error instanceof Error ? error.message : "Internal server error";
    return NextResponse.json({ error: message }, { status: 500 });
  }
}
