import { NextRequest, NextResponse } from "next/server";
import { apiFetch } from "@/lib/api-client";

export async function POST(
  request: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  try {
    const { id } = await params;
    const body = await request.json();
    const data = await apiFetch(`/v1/shortlists/${id}/candidates`, { method: "POST", body });
    return NextResponse.json(data);
  } catch (error) {
    const message = error instanceof Error ? error.message : "Internal server error";
    return NextResponse.json({ error: message }, { status: 500 });
  }
}
