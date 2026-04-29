import { NextResponse } from "next/server";
import { apiFetch } from "@/lib/api-client";

export async function GET() {
  try {
    const data = await apiFetch("/v1/hitl/stats");
    return NextResponse.json(data);
  } catch (error) {
    const message = error instanceof Error ? error.message : "Internal server error";
    return NextResponse.json({ error: message }, { status: 500 });
  }
}
