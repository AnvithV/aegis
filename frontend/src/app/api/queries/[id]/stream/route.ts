import { NextRequest } from "next/server";

export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  const { id } = await params;
  const baseUrl = process.env.AEGIS_API_URL;
  const token = process.env.AEGIS_API_TOKEN;

  const response = await fetch(`${baseUrl}/v1/queries/${id}/stream`, {
    headers: { Authorization: `Bearer ${token}` },
  });

  return new Response(response.body, {
    headers: {
      "Content-Type": "text/event-stream",
      "Cache-Control": "no-cache",
      Connection: "keep-alive",
    },
  });
}
