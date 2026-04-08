import { describe, it, expect, vi, beforeEach } from "vitest";
import { BatchProcessor } from "@core/batch";
import type { JiraConfig } from "@core/config";
import { JiraClient } from "@core/jiraClient";

const baseConfig = {
  jira_server: "https://example.atlassian.net/",
  jira_token: "token",
  "project-id": "PROJ"
} as JiraConfig;

describe("BatchProcessor", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("cria issues principais e subtasks", async () => {
    const client = {
      createIssue: vi.fn().mockResolvedValue({ key: "PROJ-1" }),
      updateIssue: vi.fn(),
      deleteIssue: vi.fn()
    } as unknown as InstanceType<typeof JiraClient>;
    const processor = new BatchProcessor(baseConfig, { client });
    const logs = await processor.createIssues([
      { Summary: "Pai", "Issue Type": "Story" },
      { Summary: "Filho", "Issue Type": "Sub-task", "Parent ID": "PROJ-1" }
    ]);
    expect(logs).toHaveLength(2);
    expect(client.createIssue).toHaveBeenCalledTimes(2);
  });

  it("atualiza issues", async () => {
    const client = {
      createIssue: vi.fn(),
      updateIssue: vi.fn().mockResolvedValue(undefined),
      deleteIssue: vi.fn()
    } as unknown as InstanceType<typeof JiraClient>;
    const processor = new BatchProcessor(baseConfig, { client });
    const logs = await processor.updateIssues([
      { issue_key: "PROJ-1", Assignee: "user@example.com" }
    ]);
    expect(logs).toHaveLength(1);
    expect(client.updateIssue).toHaveBeenCalledWith("PROJ-1", expect.any(Object));
  });

  it("deleta issues", async () => {
    const client = {
      createIssue: vi.fn(),
      updateIssue: vi.fn(),
      deleteIssue: vi.fn().mockResolvedValue(undefined)
    } as unknown as InstanceType<typeof JiraClient>;
    const processor = new BatchProcessor(baseConfig, { client });
    const logs = await processor.deleteIssues([
      { issue_key: "PROJ-1" }
    ]);
    expect(logs).toHaveLength(1);
    expect(client.deleteIssue).toHaveBeenCalledWith("PROJ-1");
  });
});
