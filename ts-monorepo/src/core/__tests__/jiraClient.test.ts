import { describe, it, expect, vi } from "vitest";
import { JiraClient } from "@core/jiraClient";

const config = {
  jira_server: "https://example.atlassian.net/",
  jira_token: "token"
} as const;

describe("JiraClient", () => {
  it("manda payload correto na criação", async () => {
    vi.spyOn(global, "fetch").mockResolvedValueOnce({
      ok: true,
      status: 201,
      headers: new Headers({ "content-type": "application/json" }),
      json: async () => ({ key: "PROJ-1", id: "1", self: "url" })
    } as unknown as Response);

    const client = new JiraClient(config);
    const created = await client.createIssue({
      project: { key: "PROJ" },
      summary: "Task",
      issuetype: { name: "Story" }
    });
    expect(created.key).toBe("PROJ-1");
  });

  it("propaga erro em resposta inválida", async () => {
    vi.spyOn(global, "fetch").mockResolvedValueOnce({
      ok: false,
      status: 400,
      headers: new Headers({ "content-type": "application/json" }),
      json: async () => ({ error: "bad" })
    } as unknown as Response);

    const client = new JiraClient(config);
    await expect(
      client.createIssue({ project: { key: "PROJ" }, summary: "Task", issuetype: { name: "Story" } })
    ).rejects.toThrow();
  });
});
