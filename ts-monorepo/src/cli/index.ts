#!/usr/bin/env node
import { Command } from "commander";
import { readFile } from "fs/promises";
import { loadConfig, parseCsv, BatchProcessor, RankingService } from "@core/index";

const program = new Command();

program
  .name("smarter-jira")
  .description("CLI Smarter Jira em TypeScript")
  .version("0.1.0");

program
  .command("import")
  .description("Cria, deleta ou atualiza issues a partir de CSV")
  .requiredOption("-c, --config <path>", "Arquivo de configuração JSON")
  .requiredOption("--csv <path>", "Arquivo CSV de entrada")
  .option("--action <action>", "create|delete|update", "create")
  .action(async (options) => {
    const config = await loadConfig(options.config);
    const csvContent = await readFile(options.csv, "utf-8");
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
        throw new Error(`Ação inválida: ${options.action}`);
    }
    console.log("Processo finalizado.");
  });

program
  .command("rank")
  .description("Reordena issues conforme critérios do rank_issues.py original")
  .requiredOption("-c, --config <path>", "Arquivo de configuração JSON")
  .option("--parent-key <key>", "Issue pai para ordenar suas filhas")
  .option("--project-id <id>", "ID do projeto para ordenar todos os épicos")
  .option("--rank-by <list>", "Critérios separados por vírgula")
  .option("--order <list>", "Direções (asc/desc) separadas por vírgula")
  .option("--status-order <list>", "Ordem customizada de status")
  .option("--issuetype-order <list>", "Ordem customizada de tipos")
  .option("--epic-order <list>", "Ordem customizada de épicos")
  .option("--dry-run", "Mostra a ordem sem aplicar", false)
  .option("--brief", "Saída resumida", false)
  .action(async (options) => {
    const config = await loadConfig(options.config);
    const service = new RankingService(config);

    const rankBy = normalizeList(options.rankBy ?? config["rank-by"]);
    if (!rankBy || rankBy.length === 0) {
      throw new Error("É necessário fornecer --rank-by ou configurar 'rank-by' no JSON");
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
      if (!key) throw new Error("'parent-key' não informado");
      await service.rankChildren(key, payload);
    } else if (options.projectId ?? config["project-id"]) {
      const projectId = options.projectId ?? config["project-id"];
      if (!projectId) throw new Error("'project-id' não informado");
      await service.rankProjectEpics(projectId, payload);
    } else if (config["sprint"]) {
      // TODO: suportar modo sprint posteriormente
      throw new Error("Modo sprint ainda não implementado");
    } else {
      throw new Error("Forneça --parent-key, --project-id ou configure 'parent-key'/'project-id' no JSON");
    }
  });

program.parseAsync(process.argv);

function normalizeList(value?: string | string[]): string[] | undefined {
  if (!value) return undefined;
  if (Array.isArray(value)) return value;
  return value.split(",").map((item) => item.trim()).filter(Boolean);
}
