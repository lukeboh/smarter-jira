import { JiraClient } from "./jiraClient";
import type { JiraConfig } from "./config";
import { buildComparator } from "./rankComparators";

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

  constructor(private readonly config: JiraConfig, private readonly overrides: { client?: JiraClient } = {}) {
    this.client = overrides.client ?? new JiraClient(config);
  }

  async rankChildren(parentKey: string, options: RankOptions): Promise<RankResult> {
    const parentIssue = await this.client.getIssue(parentKey, ["issuetype"]);
    const jql = parentIssue.fields.issuetype && (parentIssue.fields.issuetype as { name: string }).name === "Epic"
      ? `'Epic Link' = '${parentKey}' ORDER BY Rank ASC`
      : `parent = '${parentKey}' ORDER BY Rank ASC`;
    const issues = await this.client.searchIssues(jql, this.buildFields(options));
    return this.processCollection(parentKey, issues, options);
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

  private buildFields(options: RankOptions): string[] {
    const fields = new Set<string>(["priority", "status", "issuetype"]);
    options.rankBy.forEach((criterion) => {
      if (!fields.has(criterion) && !["key", "epic"].includes(criterion)) {
        fields.add(criterion);
      }
    });
    if (options.rankBy.includes("epic")) {
      fields.add("epic");
      fields.add("Epic");
    }
    return Array.from(fields);
  }

  private async processCollection(label: string, issues: Array<{ key: string; fields: Record<string, unknown> }>, options: RankOptions): Promise<RankResult> {
    if (issues.length === 0) {
      if (!options.brief) {
        console.log(`${label}: nenhuma issue para ordenar.`);
      }
      return { analyzed: 0, moved: 0 };
    }

    const comparator = buildComparator(options, options.statusOrder, options.issuetypeOrder, options.epicOrder);
    const sorted = [...issues].sort(comparator);

    const currentOrder = issues.map((issue) => issue.key);
    const desiredOrder = sorted.map((issue) => issue.key);

    if (arraysEqual(currentOrder, desiredOrder)) {
      if (!options.brief) {
        console.log(`${label}: ordem já está correta.`);
      }
      return { analyzed: issues.length, moved: 0 };
    }

    const differences = countDifferences(currentOrder, desiredOrder);

    if (options.dryRun) {
      reportOrder(label, issues, sorted, options.brief ?? false);
      return {
        analyzed: issues.length,
        moved: differences
      };
    }

    reportOrder(label, issues, sorted, options.brief ?? false);

    for (let i = 1; i < sorted.length; i++) {
      const current = sorted[i].key;
      const after = sorted[i - 1].key;
      if (current !== currentOrder[i]) {
        await this.client.rankIssueAfter(current, after);
      }
    }

    return {
      analyzed: issues.length,
      moved: differences
    };
  }
}

function arraysEqual(a: string[], b: string[]): boolean {
  return a.length === b.length && a.every((value, index) => value === b[index]);
}

function countDifferences(a: string[], b: string[]): number {
  return a.reduce((acc, value, index) => (value === b[index] ? acc : acc + 1), 0);
}

function reportOrder(
  label: string,
  current: Array<{ key: string; fields: Record<string, unknown> }>,
  sorted: Array<{ key: string; fields: Record<string, unknown> }>,
  brief: boolean
): void {
  if (brief) {
    console.log(`${label}: ${sorted.length} issues ordenadas.`);
    return;
  }

  console.log(`--- Ordem atual (${label}) ---`);
  current.forEach((issue, index) => {
    console.log(`  ${index + 1}. ${issue.key}`);
  });

  console.log(`--- Ordem proposta (${label}) ---`);
  sorted.forEach((issue, index) => {
    const epic = issue.fields["epic"] ?? issue.fields["Epic"] ?? "";
    console.log(`  ${index + 1}. ${issue.key} ${epic ? `(Epic: ${epic})` : ""}`);
  });
}
