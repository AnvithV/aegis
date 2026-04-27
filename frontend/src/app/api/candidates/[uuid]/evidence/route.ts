import { NextRequest, NextResponse } from "next/server";
import { apiFetch } from "@/lib/api-client";
import type { EvidenceTrail } from "@/types/api";

export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ uuid: string }> }
) {
  try {
    const { uuid } = await params;
    const data = await apiFetch<EvidenceTrail>(`/v1/candidates/${uuid}/evidence`);
    return NextResponse.json(data);
  } catch (error) {
    const message = error instanceof Error ? error.message : "Internal server error";
    return NextResponse.json({ error: message }, { status: 500 });
  }
}
