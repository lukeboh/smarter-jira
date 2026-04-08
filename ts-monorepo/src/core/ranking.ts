import { JiraClient } from "./jiraClient";
import type { JiraConfig } from "./config";

export interface RankOptions {
  rankBy: string[];
  order?: string[];
  statusOrder?: string[];
  issuetypeOrder?: string[];
  epicOrder?: string[];
  dryRun?: boolean;
  brief?: boolean;
}

export interface RankResult {
  analyzed: number;
  moved: number;
}

export class RankingService {
  private client: JiraClient;

  constructor(private readonly config: JiraConfig) {
    this.client = new JiraClient(config);
  }

  async rankChildren(parentKey: string, options: RankOptions): Promise<RankResult> {
    const jql = `parent = '${parentKey}' ORDER BY Rank ASC`;
    const issues = await this.client.searchIssues(jql);
    return this.rankCollection(parentKey, issues, options);
  }

  async rankProjectEpics(projectKey: string, options: RankOptions): Promise<RankResult> {
    const jql = `project = '${projectKey}' AND issuetype = Epic ORDER BY key ASC`;
    const epics = await this.client.searchIssues(jql);
    let analyzed = 0;
    let moved = 0;
    for (const epic of epics) {
      const result = await this.rankChildren(epic.key, options);
      analyzed += result.analyzed;
      moved += result.moved;
    }
    return { analyzed, moved };
  }

  async rankCollection(label: string, issues: unknown[], options: RankOptions): Promise<RankResult> {
    // TODO: Implementar lógica completa alinhada ao rank_issues.py
    console.log(`Ranking '${label}' com opções`, options);
    return { analyzed: issues.length, moved: 0 };
  }
}
