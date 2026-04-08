import { jiraRequest } from "./http";
import type { JiraConfig } from "./config";

export interface CreateIssueResponse {
  id: string;
  key: string;
  self: string;
}

export interface JiraIssueCreateFields {
  project: { key: string };
  summary: string;
  description?: string;
  issuetype: { name: string };
  reporter?: { name: string };
  assignee?: { name: string };
  parent?: { key: string };
  components?: Array<{ name: string }>;
  [customField: string]: unknown;
}

export interface JiraIssueUpdateFields {
  assignee?: { name: string };
  [customField: string]: unknown;
}

export interface JiraIssue {
  key: string;
  id: string;
  fields: Record<string, unknown>;
}

export class JiraClient {
  constructor(private readonly config: JiraConfig) {}

  async createIssue(fields: JiraIssueCreateFields): Promise<CreateIssueResponse> {
    const response = await jiraRequest<CreateIssueResponse>(this.config, {
      path: "rest/api/2/issue",
      method: "POST",
      body: JSON.stringify({ fields })
    });

    if (!response.ok || !response.data) {
      throw new Error(
        `Falha ao criar issue: status=${response.status}, erro=${JSON.stringify(response.error)}`
      );
    }

    return response.data;
  }

  async updateIssue(issueKey: string, fields: JiraIssueUpdateFields): Promise<void> {
    const response = await jiraRequest(this.config, {
      path: `rest/api/2/issue/${issueKey}`,
      method: "PUT",
      body: JSON.stringify({ fields })
    });

    if (!response.ok) {
      throw new Error(
        `Falha ao atualizar issue ${issueKey}: status=${response.status}, erro=${JSON.stringify(response.error)}`
      );
    }
  }

  async deleteIssue(issueKey: string): Promise<void> {
    const response = await jiraRequest(this.config, {
      path: `rest/api/2/issue/${issueKey}`,
      method: "DELETE"
    });

    if (!response.ok) {
      throw new Error(
        `Falha ao deletar issue ${issueKey}: status=${response.status}, erro=${JSON.stringify(response.error)}`
      );
    }
  }

  async searchIssues<TFields = unknown>(jql: string, fields?: string[]): Promise<Array<JiraIssue & { fields: TFields }>> {
    const response = await jiraRequest<{ issues: Array<JiraIssue & { fields: TFields }> }>(this.config, {
      path: "rest/api/2/search",
      method: "POST",
      body: JSON.stringify({ jql, maxResults: -1, fields })
    });

    if (!response.ok || !response.data) {
      throw new Error(
        `Falha ao buscar issues: status=${response.status}, erro=${JSON.stringify(response.error)}`
      );
    }

    return response.data.issues;
  }
}
