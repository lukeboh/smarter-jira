#!/usr/bin/env node
import { Command } from "commander";
import { readFile } from "fs/promises";
import { loadConfig, parseCsv, BatchProcessor } from "@core/index";

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

program.parseAsync(process.argv);
