#!/usr/bin/env node
"use strict";
var __create = Object.create;
var __defProp = Object.defineProperty;
var __getOwnPropDesc = Object.getOwnPropertyDescriptor;
var __getOwnPropNames = Object.getOwnPropertyNames;
var __getProtoOf = Object.getPrototypeOf;
var __hasOwnProp = Object.prototype.hasOwnProperty;
var __copyProps = (to, from, except, desc) => {
  if (from && typeof from === "object" || typeof from === "function") {
    for (let key of __getOwnPropNames(from))
      if (!__hasOwnProp.call(to, key) && key !== except)
        __defProp(to, key, { get: () => from[key], enumerable: !(desc = __getOwnPropDesc(from, key)) || desc.enumerable });
  }
  return to;
};
var __toESM = (mod, isNodeMode, target) => (target = mod != null ? __create(__getProtoOf(mod)) : {}, __copyProps(
  // If the importer is in node compatibility mode or this is not an ESM
  // file that has been converted to a CommonJS file using a Babel-
  // compatible transform (i.e. "__esModule" has not been set), then set
  // "default" to the CommonJS "module.exports" for node compatibility.
  isNodeMode || !mod || !mod.__esModule ? __defProp(target, "default", { value: mod, enumerable: true }) : target,
  mod
));

// src/cli/index.ts
var import_commander = require("commander");
var import_promises2 = require("fs/promises");

// src/core/config.ts
var import_promises = require("fs/promises");
var import_path = require("path");
var import_zod = require("zod");
var configSchema = import_zod.z.object({
  "jira_server": import_zod.z.string().url(),
  "jira_token": import_zod.z.string().min(1),
  "project-id": import_zod.z.string().optional(),
  "parent-key": import_zod.z.string().optional(),
  "rank-by": import_zod.z.array(import_zod.z.string()).optional(),
  "order": import_zod.z.array(import_zod.z.string()).optional(),
  "status-order": import_zod.z.array(import_zod.z.string()).optional(),
  "issuetype-order": import_zod.z.array(import_zod.z.string()).optional(),
  "epic-order": import_zod.z.array(import_zod.z.string()).optional(),
  "components_to_track": import_zod.z.string().optional(),
  "default_reporter": import_zod.z.string().optional(),
  "default_assignee": import_zod.z.string().optional(),
  "default_component": import_zod.z.string().optional(),
  "default_customfield_10247": import_zod.z.string().optional(),
  "epic_link_field_id": import_zod.z.string().optional(),
  "sprint": import_zod.z.string().optional()
}).passthrough();
async function loadConfig(path) {
  const absPath = (0, import_path.resolve)(path);
  const raw = await (0, import_promises.readFile)(absPath, "utf-8");
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
var import_papaparse = __toESM(require("papaparse"), 1);
function parseCsv(content, options = {}) {
  const { header = true, transform } = options;
  const result = import_papaparse.default.parse(content, {
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
  async getFields() {
    const response = await jiraRequest(this.config, {
      path: "rest/api/2/field",
      method: "GET"
    });
    if (!response.ok || !response.data) {
      throw new Error(
        `Falha ao buscar campos: status=${response.status}, erro=${JSON.stringify(response.error)}`
      );
    }
    return response.data;
  }
  async rankIssueAfter(issueKey, rankAfterIssue) {
    const response = await jiraRequest(this.config, {
      path: "rest/agile/1.0/issue/rank",
      method: "PUT",
      body: JSON.stringify({
        issues: [issueKey],
        rankAfterIssue
      })
    });
    if (!response.ok) {
      throw new Error(
        `Falha ao reordenar issue ${issueKey} ap\xF3s ${rankAfterIssue}: status=${response.status}, erro=${JSON.stringify(response.error)}`
      );
    }
  }
  async getIssue(issueKey, fields) {
    const response = await jiraRequest(this.config, {
      path: `rest/api/2/issue/${issueKey}`,
      method: "GET",
      searchParams: fields ? { fields: fields.join(",") } : void 0
    });
    if (!response.ok || !response.data) {
      throw new Error(
        `Falha ao buscar issue ${issueKey}: status=${response.status}, erro=${JSON.stringify(response.error)}`
      );
    }
    return response.data;
  }
};

// src/core/batch.ts
var BatchProcessor = class {
  constructor(config, options = {}) {
    this.config = config;
    this.client = options.client ?? new JiraClient(config);
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

// src/core/rankComparators.ts
function buildComparator(options, statusOrder, issuetypeOrder, epicOrder) {
  const order = normalizeOrder(options.rankBy, options.order);
  const statusMap = mapOrder(statusOrder);
  const issuetypeMap = mapOrder(issuetypeOrder);
  const epicMap = mapOrder(epicOrder);
  return (a, b) => {
    for (let i = 0; i < options.rankBy.length; i++) {
      const criterion = options.rankBy[i];
      const direction = order[i];
      const valueA = getCriterionValue(a, criterion, statusMap, issuetypeMap, epicMap);
      const valueB = getCriterionValue(b, criterion, statusMap, issuetypeMap, epicMap);
      const comparison = compareValues(valueA, valueB);
      if (comparison !== 0) {
        return direction === "asc" ? comparison : -comparison;
      }
    }
    return 0;
  };
}
function normalizeOrder(rankBy, order) {
  if (!order || order.length === 0) {
    return rankBy.map(() => "asc");
  }
  if (order.length === 1) {
    return rankBy.map(() => order[0] ?? "asc");
  }
  if (order.length !== rankBy.length) {
    throw new Error("N\xFAmero de dire\xE7\xF5es de ordena\xE7\xE3o diferente do n\xFAmero de crit\xE9rios");
  }
  return order;
}
function mapOrder(values) {
  if (!values) return void 0;
  const map = /* @__PURE__ */ new Map();
  values.forEach((value, index) => map.set(value.toLowerCase(), index));
  return map;
}
function getCriterionValue(issue, criterion, statusMap, issuetypeMap, epicMap) {
  switch (criterion) {
    case "key":
      return parseIssueKey(issue.key);
    case "priority":
      return Number(issue.fields.priority?.id ?? Number.MAX_SAFE_INTEGER);
    case "status": {
      const statusName = issue.fields.status?.name;
      if (statusName && statusMap) {
        const normalized = statusMap.get(statusName.toLowerCase());
        if (normalized !== void 0) return normalized;
      }
      const categoryId = issue.fields.status?.statusCategory?.id;
      if (categoryId) {
        const categoryMap = { 2: 0, 4: 1, 3: 2 };
        return categoryMap[categoryId] ?? 99;
      }
      return Number.MAX_SAFE_INTEGER;
    }
    case "issuetype": {
      const name = issue.fields.issuetype?.name;
      if (name && issuetypeMap) {
        const normalized = issuetypeMap.get(name.toLowerCase());
        if (normalized !== void 0) return normalized;
      }
      return name ?? "";
    }
    case "epic": {
      const epic = issue.fields["epic"] ?? issue.fields["Epic"];
      if (typeof epic === "string" && epicMap) {
        const normalized = epicMap.get(epic.toLowerCase());
        if (normalized !== void 0) return normalized;
      }
      return epic ?? "";
    }
    default:
      return issue.fields[criterion] ?? issue[criterion];
  }
}
function compareValues(a, b) {
  if (a === b) return 0;
  if (a === void 0 || a === null) return 1;
  if (b === void 0 || b === null) return -1;
  if (typeof a === "number" && typeof b === "number") {
    return a - b;
  }
  if (Array.isArray(a) && Array.isArray(b)) {
    const length = Math.max(a.length, b.length);
    for (let i = 0; i < length; i++) {
      const result = compareValues(a[i], b[i]);
      if (result !== 0) return result;
    }
    return 0;
  }
  return String(a).localeCompare(String(b));
}
function parseIssueKey(key) {
  const [prefix, number] = key.split("-");
  const parsed = Number(number);
  if (Number.isNaN(parsed)) {
    return [key, Number.MAX_SAFE_INTEGER];
  }
  return [prefix, parsed];
}

// src/core/ranking.ts
var RankingService = class {
  constructor(config, overrides = {}) {
    this.config = config;
    this.overrides = overrides;
    this.client = overrides.client ?? new JiraClient(config);
  }
  async rankChildren(parentKey, options) {
    const parentIssue = await this.client.getIssue(parentKey, ["issuetype"]);
    const jql = parentIssue.fields.issuetype && parentIssue.fields.issuetype.name === "Epic" ? `'Epic Link' = '${parentKey}' ORDER BY Rank ASC` : `parent = '${parentKey}' ORDER BY Rank ASC`;
    const issues = await this.client.searchIssues(jql, this.buildFields(options));
    return this.processCollection(parentKey, issues, options);
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
  buildFields(options) {
    const fields = /* @__PURE__ */ new Set(["priority", "status", "issuetype"]);
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
  async processCollection(label, issues, options) {
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
        console.log(`${label}: ordem j\xE1 est\xE1 correta.`);
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
};
function arraysEqual(a, b) {
  return a.length === b.length && a.every((value, index) => value === b[index]);
}
function countDifferences(a, b) {
  return a.reduce((acc, value, index) => value === b[index] ? acc : acc + 1, 0);
}
function reportOrder(label, current, sorted, brief) {
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

// src/cli/index.ts
var program = new import_commander.Command();
program.name("smarter-jira").description("CLI Smarter Jira em TypeScript").version("0.1.0");
program.command("import").description("Cria, deleta ou atualiza issues a partir de CSV").requiredOption("-c, --config <path>", "Arquivo de configura\xE7\xE3o JSON").requiredOption("--csv <path>", "Arquivo CSV de entrada").option("--action <action>", "create|delete|update", "create").action(async (options) => {
  const config = await loadConfig(options.config);
  const csvContent = await (0, import_promises2.readFile)(options.csv, "utf-8");
  const rows = parseCsv(csvContent);
  const processor = new BatchProcessor(config);
  switch (options.action) {
    case "create":
      await processor.createIssues(rows);
      break;
    case "delete":
      await processor.deleteIssues(rows);
      break;
    case "update":
      await processor.updateIssues(rows);
      break;
    default:
      throw new Error(`A\xE7\xE3o inv\xE1lida: ${options.action}`);
  }
  console.log("Processo finalizado.");
});
program.command("rank").description("Reordena issues conforme crit\xE9rios do rank_issues.py original").requiredOption("-c, --config <path>", "Arquivo de configura\xE7\xE3o JSON").option("--parent-key <key>", "Issue pai para ordenar suas filhas").option("--project-id <id>", "ID do projeto para ordenar todos os \xE9picos").option("--rank-by <list>", "Crit\xE9rios separados por v\xEDrgula").option("--order <list>", "Dire\xE7\xF5es (asc/desc) separadas por v\xEDrgula").option("--status-order <list>", "Ordem customizada de status").option("--issuetype-order <list>", "Ordem customizada de tipos").option("--epic-order <list>", "Ordem customizada de \xE9picos").option("--dry-run", "Mostra a ordem sem aplicar", false).option("--brief", "Sa\xEDda resumida", false).action(async (options) => {
  const config = await loadConfig(options.config);
  const service = new RankingService(config);
  const rankBy = normalizeList(options.rankBy ?? config["rank-by"]);
  if (!rankBy || rankBy.length === 0) {
    throw new Error("\xC9 necess\xE1rio fornecer --rank-by ou configurar 'rank-by' no JSON");
  }
  const payload = {
    rankBy,
    order: normalizeList(options.order ?? config["order"]),
    statusOrder: normalizeList(options["status-order"] ?? config["status-order"]),
    issuetypeOrder: normalizeList(options["issuetype-order"] ?? config["issuetype-order"]),
    epicOrder: normalizeList(options["epic-order"] ?? config["epic-order"]),
    dryRun: Boolean(options.dryRun),
    brief: Boolean(options.brief)
  };
  if (options.parentKey ?? config["parent-key"]) {
    const key = options.parentKey ?? config["parent-key"];
    if (!key) throw new Error("'parent-key' n\xE3o informado");
    await service.rankChildren(key, payload);
  } else if (options.projectId ?? config["project-id"]) {
    const projectId = options.projectId ?? config["project-id"];
    if (!projectId) throw new Error("'project-id' n\xE3o informado");
    await service.rankProjectEpics(projectId, payload);
  } else if (config["sprint"]) {
    throw new Error("Modo sprint ainda n\xE3o implementado");
  } else {
    throw new Error("Forne\xE7a --parent-key, --project-id ou configure 'parent-key'/'project-id' no JSON");
  }
});
program.parseAsync(process.argv);
function normalizeList(value) {
  if (!value) return void 0;
  if (Array.isArray(value)) return value;
  return value.split(",").map((item) => item.trim()).filter(Boolean);
}
