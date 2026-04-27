import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

export function middleware(request: NextRequest) {
  // For API routes, just pass through -- the api-client handles token injection server-side
  if (request.nextUrl.pathname.startsWith("/api/")) {
    return NextResponse.next();
  }

  // For page routes, pass through (internal tool, no login required)
  return NextResponse.next();
}

export const config = {
  matcher: ["/api/:path*", "/((?!_next/static|_next/image|favicon.ico).*)"],
};
