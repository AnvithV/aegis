import { NextRequest, NextResponse } from "next/server";
import { apiFetch } from "@/lib/api-client";
import type { QueryRequest, QueryListResponse } from "@/types/api";

export async function POST(request: NextRequest) {
  try {
    const body: QueryRequest & { query_type_override?: string } = await request.json();
    const data = await apiFetch<{ job_id: string; status: string }>("/v1/queries", {
      method: "POST",
      body,
    });
    return NextResponse.json({ job_id: data.job_id, status: data.status });
  } catch (error) {
    const message = error instanceof Error ? error.message : "Internal server error";
    return NextResponse.json({ error: message }, { status: 500 });
  }
}

export async function GET(request: NextRequest) {
  try {
    const { searchParams } = new URL(request.url);
    const page = searchParams.get("page") || "1";
    const perPage = searchParams.get("per_page") || "20";
    const data = await apiFetch<QueryListResponse>("/v1/queries", {
      params: { page, per_page: perPage },
    });
    return NextResponse.json(data);
  } catch (error) {
    const message = error instanceof Error ? error.message : "Internal server error";
    return NextResponse.json({ error: message }, { status: 500 });
  }
}
