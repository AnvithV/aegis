import { NextRequest, NextResponse } from "next/server";
import { apiFetch } from "@/lib/api-client";

export async function GET() {
  try {
    const data = await apiFetch("/v1/shortlists");
    return NextResponse.json(data);
  } catch (error) {
    const message = error instanceof Error ? error.message : "Internal server error";
    return NextResponse.json({ error: message }, { status: 500 });
  }
}

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const data = await apiFetch("/v1/shortlists", { method: "POST", body });
    return NextResponse.json(data);
  } catch (error) {
    const message = error instanceof Error ? error.message : "Internal server error";
    return NextResponse.json({ error: message }, { status: 500 });
  }
}
