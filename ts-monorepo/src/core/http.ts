import type { JiraConfig } from "./config";

export interface JiraRequestOptions extends RequestInit {
  path: string;
  searchParams?: Record<string, string | number | boolean | undefined>;
}

export interface JiraResponse<T> {
  ok: boolean;
  status: number;
  data: T | null;
  error?: unknown;
}

function buildUrl(config: JiraConfig, path: string, searchParams?: JiraRequestOptions["searchParams"]): string {
  const base = new URL(path, config["jira_server"]);
  if (searchParams) {
    Object.entries(searchParams).forEach(([key, value]) => {
      if (value === undefined) return;
      base.searchParams.set(key, String(value));
    });
  }
  return base.toString();
}

export async function jiraRequest<T = unknown>(config: JiraConfig, options: JiraRequestOptions): Promise<JiraResponse<T>> {
  const url = buildUrl(config, options.path, options.searchParams);
  const headers = new Headers(options.headers);
  headers.set("Authorization", `Bearer ${config["jira_token"]}`);
  headers.set("Content-Type", headers.get("Content-Type") ?? "application/json");

  try {
    const response = await fetch(url, { ...options, headers });
    const contentType = response.headers.get("content-type") ?? "";
    const isJson = contentType.includes("application/json");
    const data = (isJson ? await response.json() : await response.text()) as T;

    if (!response.ok) {
      return { ok: false, status: response.status, data: null, error: data };
    }

    return { ok: true, status: response.status, data };
  } catch (error) {
    return { ok: false, status: 0, data: null, error };
  }
}
