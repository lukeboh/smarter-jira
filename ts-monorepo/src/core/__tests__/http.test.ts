import { describe, it, expect, vi } from "vitest";
import { jiraRequest } from "@core/http";

const config = {
  jira_server: "https://example.atlassian.net/",
  jira_token: "token"
} as const;

describe("jiraRequest", () => {
  it("realiza request com headers de autorização", async () => {
    const fetchSpy = vi.spyOn(global, "fetch").mockResolvedValueOnce({
      ok: true,
      status: 200,
      headers: new Headers({ "content-type": "application/json" }),
      json: async () => ({ ok: true })
    } as unknown as Response);

    const result = await jiraRequest(config, { path: "rest/api/2/issue", method: "GET" });
    expect(result.ok).toBe(true);
    expect(fetchSpy).toHaveBeenCalledWith(
      "https://example.atlassian.net/rest/api/2/issue",
      expect.objectContaining({
        headers: expect.any(Headers)
      })
    );
  });

  it("propaga erro quando request falha", async () => {
    vi.spyOn(global, "fetch").mockRejectedValueOnce(new Error("network"));
    const result = await jiraRequest(config, { path: "rest/api/2/issue", method: "GET" });
    expect(result.ok).toBe(false);
    expect(result.error).toBeInstanceOf(Error);
  });
});
