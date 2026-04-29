import { NextRequest, NextResponse } from "next/server";
import { apiFetch } from "@/lib/api-client";

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const specialty = body?.specialty ?? "basic_research";
    const data = await apiFetch(
      `/v1/refit/trigger?specialty=${encodeURIComponent(specialty)}`,
      { method: "POST" }
    );
    return NextResponse.json(data);
  } catch (error) {
    const message = error instanceof Error ? error.message : "Internal server error";
    return NextResponse.json({ error: message }, { status: 500 });
  }
}
