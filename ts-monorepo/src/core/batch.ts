import type { JiraConfig } from "./config";
import { JiraClient, JiraIssueCreateFields, JiraIssueUpdateFields } from "./jiraClient";

export interface ImportRow {
  [key: string]: string | undefined;
  "Issue ID"?: string;
  "Parent ID"?: string;
  "Summary"?: string;
  "Description"?: string;
  "Issue Type"?: string;
  "Reporter"?: string;
  "Assignee"?: string;
  "Epic Link"?: string;
}

export interface LogEntry {
  issueKey: string;
  action: "C" | "U" | "D";
  payload: Record<string, unknown>;
}

export interface BatchProcessorOptions {
  logger?: { info: (...args: unknown[]) => void; warn: (...args: unknown[]) => void; error: (...args: unknown[]) => void };
  client?: JiraClient;
}

export class BatchProcessor {
  private client: JiraClient;

  constructor(private readonly config: JiraConfig, options: BatchProcessorOptions = {}) {
    this.client = options.client ?? new JiraClient(config);
    this.logger = options.logger ?? console;
  }

  private logger: Required<BatchProcessorOptions>["logger"];

  async createIssues(rows: ImportRow[]): Promise<LogEntry[]> {
    const logs: LogEntry[] = [];
    const parentMap = new Map<string, string>();

    for (const row of rows.filter((issue) => !issue["Parent ID"])) {
      const created = await this.createIssue(row);
      if (!created) continue;
      const issueId = row["Issue ID"];
      if (issueId) {
        parentMap.set(issueId, created.key);
      }
      logs.push({ issueKey: created.key, action: "C", payload: row });
    }

    for (const row of rows.filter((issue) => issue["Parent ID"])) {
      const parentId = row["Parent ID"];
      const parentKey = (parentId && parentMap.get(parentId)) ?? parentId;
      const created = await this.createIssue(row, parentKey);
      if (!created) continue;
      logs.push({ issueKey: created.key, action: "C", payload: row });
    }

    return logs;
  }

  async deleteIssues(rows: ImportRow[]): Promise<LogEntry[]> {
    const logs: LogEntry[] = [];
    for (const row of rows) {
      const key = row["issue_key"] ?? row["Issue Key"] ?? row["Key"];
      if (!key) {
        this.logger.warn("Linha ignorada por não conter issue key", row);
        continue;
      }
      await this.client.deleteIssue(key);
      logs.push({ issueKey: key, action: "D", payload: row });
    }
    return logs;
  }

  async updateIssues(rows: ImportRow[]): Promise<LogEntry[]> {
    const logs: LogEntry[] = [];
    for (const row of rows) {
      const key = row["issue_key"] ?? row["Issue Key"] ?? row["Key"];
      if (!key) {
        this.logger.warn("Linha ignorada por não conter issue key", row);
        continue;
      }
      const payload: JiraIssueUpdateFields = {};
      const assignee = row["Assignee"] ?? this.config["default_assignee"];
      if (assignee) {
        payload.assignee = { name: assignee.split("@")[0] };
      }
      await this.client.updateIssue(key, payload);
      logs.push({ issueKey: key, action: "U", payload: row });
    }
    return logs;
  }

  private async createIssue(row: ImportRow, parentKey?: string): Promise<{ key: string } | null> {
    const reporterEmail = row["Reporter"] ?? this.config["default_reporter"] ?? "";
    const assigneeEmail = row["Assignee"] ?? this.config["default_assignee"];
    const issueType = row["Issue Type"];
    const summary = row["Summary"];

    if (!issueType || !summary) {
      this.logger.error("Linha inválida, campos obrigatórios ausentes", row);
      return null;
    }

    const payload: JiraIssueCreateFields = {
      project: { key: this.config["project-id"] ?? "" },
      summary,
      description: row["Description"],
      issuetype: { name: issueType },
      components: parentKey ? undefined : this.config["default_component"] ? [{ name: this.config["default_component"] }] : undefined
    };

    if (reporterEmail) {
      payload.reporter = { name: reporterEmail.split("@")[0] };
    }
    if (assigneeEmail) {
      payload.assignee = { name: assigneeEmail.split("@")[0] };
    }
    if (parentKey) {
      payload.parent = { key: parentKey };
    } else {
      const epicLink = row["Epic Link"];
      const epicFieldId = this.config["epic_link_field_id"];
      if (epicLink && epicFieldId) {
        payload[epicFieldId] = epicLink;
      }
    }
    if (this.config["default_customfield_10247"]) {
      payload["customfield_10247"] = { value: this.config["default_customfield_10247"] };
    }

    if (!payload.project.key) {
      throw new Error("'project-id' não definido na configuração para criação de issues");
    }

    const created = await this.client.createIssue(payload);
    this.logger.info(`Issue criada: ${created.key}`);
    return created;
  }
}
