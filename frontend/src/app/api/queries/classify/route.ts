import { NextRequest, NextResponse } from "next/server";
import { apiFetch } from "@/lib/api-client";

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const data = await apiFetch("/v1/queries/classify", { method: "POST", body });
    return NextResponse.json(data);
  } catch (error) {
    const message = error instanceof Error ? error.message : "Classification failed";
    return NextResponse.json({ error: message }, { status: 500 });
  }
}
