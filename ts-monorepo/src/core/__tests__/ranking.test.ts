import { describe, it, expect, vi, beforeEach } from "vitest";
import { RankingService } from "@core/ranking";
import type { JiraConfig } from "@core/config";
import type { JiraClient } from "@core/jiraClient";

const config = {
  jira_server: "https://example.atlassian.net/",
  jira_token: "token"
} as JiraConfig;

describe("RankingService", () => {
  let client: Pick<JiraClient, "searchIssues" | "rankIssueAfter" | "getIssue" >;

  beforeEach(() => {
    client = {
      searchIssues: vi.fn(),
      rankIssueAfter: vi.fn().mockResolvedValue(undefined),
      getIssue: vi.fn().mockResolvedValue({
        key: "EPIC-1",
        id: "1",
        fields: { issuetype: { name: "Epic" } }
      })
    } as unknown as Pick<JiraClient, "searchIssues" | "rankIssueAfter" | "getIssue">;
  });

  it("não reordena quando ordem já está correta", async () => {
    client.searchIssues = vi.fn().mockResolvedValue([
      { key: "PROJ-1", fields: { status: { name: "To Do" } } },
      { key: "PROJ-2", fields: { status: { name: "Done" } } }
    ]);

    const service = new RankingService(config, { client: client as JiraClient });
    const result = await service.rankChildren("PROJ-EPIC", { rankBy: ["key"], order: ["asc"], dryRun: true });
    expect(result.moved).toBe(0);
  });

  it("aplica rank quando ordem muda", async () => {
    client.searchIssues = vi.fn().mockResolvedValue([
      { key: "PROJ-2", fields: { status: { name: "To Do" } } },
      { key: "PROJ-1", fields: { status: { name: "Done" } } }
    ]);

    const service = new RankingService(config, { client: client as JiraClient });
    const result = await service.rankChildren("PROJ-EPIC", { rankBy: ["key"], order: ["asc"] });

    expect(result.moved).toBe(2);
    expect(client.rankIssueAfter).toHaveBeenCalledWith("PROJ-2", "PROJ-1");
  });
});
