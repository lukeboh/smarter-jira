import { readFile } from "fs/promises";
import { resolve } from "path";
import { z } from "zod";

const configSchema = z.object({
  "jira_server": z.string().url(),
  "jira_token": z.string().min(1),
  "project-id": z.string().optional(),
  "parent-key": z.string().optional(),
  "rank-by": z.array(z.string()).optional(),
  "order": z.array(z.string()).optional(),
  "status-order": z.array(z.string()).optional(),
  "issuetype-order": z.array(z.string()).optional(),
  "epic-order": z.array(z.string()).optional(),
  "components_to_track": z.string().optional(),
  "default_reporter": z.string().optional(),
  "default_assignee": z.string().optional(),
  "default_component": z.string().optional(),
  "default_customfield_10247": z.string().optional(),
  "epic_link_field_id": z.string().optional(),
  "sprint": z.string().optional()
}).passthrough();

export type JiraConfig = z.infer<typeof configSchema>;

export async function loadConfig(path: string): Promise<JiraConfig> {
  const absPath = resolve(path);
  const raw = await readFile(absPath, "utf-8");
  const parsed = JSON.parse(raw);
  return configSchema.parse(parsed);
}
