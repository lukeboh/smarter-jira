// src/core/config.ts
import { readFile } from "fs/promises";
import { resolve } from "path";
import { z } from "zod";
var configSchema = z.object({
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
async function loadConfig(path) {
  const absPath = resolve(path);
  const raw = await readFile(absPath, "utf-8");
  const parsed = JSON.parse(raw);
  return configSchema.parse(parsed);
}

// src/core/http.ts
function buildUrl(config, path, searchParams) {
  const base = new URL(path, config["jira_server"]);
  if (searchParams) {
    Object.entries(searchParams).forEach(([key, value]) => {
      if (value === void 0) return;
      base.searchParams.set(key, String(value));
    });
  }
  return base.toString();
}
async function jiraRequest(config, options) {
  const url = buildUrl(config, options.path, options.searchParams);
  const headers = new Headers(options.headers);
  headers.set("Authorization", `Bearer ${config["jira_token"]}`);
  headers.set("Content-Type", headers.get("Content-Type") ?? "application/json");
  try {
    const response = await fetch(url, { ...options, headers });
    const contentType = response.headers.get("content-type") ?? "";
    const isJson = contentType.includes("application/json");
    const data = isJson ? await response.json() : await response.text();
    if (!response.ok) {
      return { ok: false, status: response.status, data: null, error: data };
    }
    return { ok: true, status: response.status, data };
  } catch (error) {
    return { ok: false, status: 0, data: null, error };
  }
}

// src/core/csv.ts
import Papa from "papaparse";
function parseCsv(content, options = {}) {
  const { header = true, transform } = options;
  const result = Papa.parse(content, {
    header,
    skipEmptyLines: true,
    transformHeader: (headerName) => headerName.trim(),
    transform: (value) => value.trim()
  });
  if (result.errors.length) {
    const messages = result.errors.map((err) => err.message).join("; ");
    throw new Error(`Falha ao processar CSV: ${messages}`);
  }
  if (!transform) {
    return result.data;
  }
  return result.data.map((row) => transform(row));
}

// src/core/logging.ts
function createLogger(level = "info") {
  const priorities = {
    debug: 10,
    info: 20,
    warn: 30,
    error: 40
  };
  const current = priorities[level];
  function allowed(target) {
    return priorities[target] >= current;
  }
  return {
    debug: (...args) => {
      if (allowed("debug")) console.debug(...args);
    },
    info: (...args) => {
      if (allowed("info")) console.info(...args);
    },
    warn: (...args) => {
      if (allowed("warn")) console.warn(...args);
    },
    error: (...args) => {
      if (allowed("error")) console.error(...args);
    }
  };
}

// src/core/jiraClient.ts
var JiraClient = class {
  constructor(config) {
    this.config = config;
  }
  async createIssue(fields) {
    const response = await jiraRequest(this.config, {
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
  async updateIssue(issueKey, fields) {
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
  async deleteIssue(issueKey) {
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
  async searchIssues(jql, fields) {
    const response = await jiraRequest(this.config, {
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
};

// src/core/batch.ts
var BatchProcessor = class {
  constructor(config, options = {}) {
    this.config = config;
    this.client = new JiraClient(config);
    this.logger = options.logger ?? console;
  }
  async createIssues(rows) {
    const logs = [];
    const parentMap = /* @__PURE__ */ new Map();
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
  async deleteIssues(rows) {
    const logs = [];
    for (const row of rows) {
      const key = row["issue_key"] ?? row["Issue Key"] ?? row["Key"];
      if (!key) {
        this.logger.warn("Linha ignorada por n\xE3o conter issue key", row);
        continue;
      }
      await this.client.deleteIssue(key);
      logs.push({ issueKey: key, action: "D", payload: row });
    }
    return logs;
  }
  async updateIssues(rows) {
    const logs = [];
    for (const row of rows) {
      const key = row["issue_key"] ?? row["Issue Key"] ?? row["Key"];
      if (!key) {
        this.logger.warn("Linha ignorada por n\xE3o conter issue key", row);
        continue;
      }
      const payload = {};
      const assignee = row["Assignee"] ?? this.config["default_assignee"];
      if (assignee) {
        payload.assignee = { name: assignee.split("@")[0] };
      }
      await this.client.updateIssue(key, payload);
      logs.push({ issueKey: key, action: "U", payload: row });
    }
    return logs;
  }
  async createIssue(row, parentKey) {
    const reporterEmail = row["Reporter"] ?? this.config["default_reporter"] ?? "";
    const assigneeEmail = row["Assignee"] ?? this.config["default_assignee"];
    const issueType = row["Issue Type"];
    const summary = row["Summary"];
    if (!issueType || !summary) {
      this.logger.error("Linha inv\xE1lida, campos obrigat\xF3rios ausentes", row);
      return null;
    }
    const payload = {
      project: { key: this.config["project-id"] ?? "" },
      summary,
      description: row["Description"],
      issuetype: { name: issueType },
      components: parentKey ? void 0 : this.config["default_component"] ? [{ name: this.config["default_component"] }] : void 0
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
      throw new Error("'project-id' n\xE3o definido na configura\xE7\xE3o para cria\xE7\xE3o de issues");
    }
    const created = await this.client.createIssue(payload);
    this.logger.info(`Issue criada: ${created.key}`);
    return created;
  }
};

// src/core/ranking.ts
var RankingService = class {
  constructor(config) {
    this.config = config;
    this.client = new JiraClient(config);
  }
  async rankChildren(parentKey, options) {
    const jql = `parent = '${parentKey}' ORDER BY Rank ASC`;
    const issues = await this.client.searchIssues(jql);
    return this.rankCollection(parentKey, issues, options);
  }
  async rankProjectEpics(projectKey, options) {
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
  async rankCollection(label, issues, options) {
    console.log(`Ranking '${label}' com op\xE7\xF5es`, options);
    return { analyzed: issues.length, moved: 0 };
  }
};
export {
  BatchProcessor,
  JiraClient,
  RankingService,
  createLogger,
  jiraRequest,
  loadConfig,
  parseCsv
};
