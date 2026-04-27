/**
 * Server-side API client for the Aegis backend.
 * This module runs ONLY on the server (in API route handlers).
 * It reads AEGIS_API_URL and AEGIS_API_TOKEN from environment variables.
 * JWT tokens never leave the server.
 */

const getBaseUrl = (): string => {
  const url = process.env.AEGIS_API_URL;
  if (!url) {
    throw new Error("AEGIS_API_URL environment variable is not set");
  }
  return url;
};

const getToken = (): string => {
  const token = process.env.AEGIS_API_TOKEN;
  if (!token) {
    throw new Error("AEGIS_API_TOKEN environment variable is not set");
  }
  return token;
};

interface FetchOptions {
  method?: string;
  body?: unknown;
  params?: Record<string, string>;
}

async function apiFetch<T>(path: string, options: FetchOptions = {}): Promise<T> {
  const baseUrl = getBaseUrl();
  const token = getToken();

  let url = `${baseUrl}${path}`;
  if (options.params) {
    const searchParams = new URLSearchParams(options.params);
    url += `?${searchParams.toString()}`;
  }

  const response = await fetch(url, {
    method: options.method || "GET",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
    },
    ...(options.body ? { body: JSON.stringify(options.body) } : {}),
  });

  if (!response.ok) {
    const errorText = await response.text().catch(() => "Unknown error");
    throw new Error(`API error ${response.status}: ${errorText}`);
  }

  return response.json() as Promise<T>;
}

export { apiFetch };
