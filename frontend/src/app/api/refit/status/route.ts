import { NextRequest, NextResponse } from "next/server";
import { apiFetch } from "@/lib/api-client";

export async function GET(request: NextRequest) {
  try {
    const specialty = request.nextUrl.searchParams.get("specialty") ?? "basic_research";
    const data = await apiFetch(
      `/v1/refit/status?specialty=${encodeURIComponent(specialty)}`
    );
    return NextResponse.json(data);
  } catch (error) {
    const message = error instanceof Error ? error.message : "Internal server error";
    return NextResponse.json({ error: message }, { status: 500 });
  }
}
