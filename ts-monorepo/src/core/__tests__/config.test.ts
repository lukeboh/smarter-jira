import { describe, it, expect } from "vitest";
import { loadConfig } from "@core/config";
import { writeFile, mkdtemp } from "fs/promises";
import { tmpdir } from "os";
import { join } from "path";

describe("loadConfig", () => {
  it("carrega e valida um arquivo de configuração válido", async () => {
    const dir = await mkdtemp(join(tmpdir(), "config-test-"));
    const filePath = join(dir, "config.json");
    await writeFile(
      filePath,
      JSON.stringify({
        jira_server: "https://example.atlassian.net/",
        jira_token: "token",
        "project-id": "PROJ",
        "rank-by": ["status"]
      })
    );

    const config = await loadConfig(filePath);
    expect(config["jira_server"]).toBe("https://example.atlassian.net/");
    expect(config["rank-by"]).toEqual(["status"]);
  });

  it("falha ao carregar arquivo inválido", async () => {
    const dir = await mkdtemp(join(tmpdir(), "config-test-"));
    const filePath = join(dir, "config.json");
    await writeFile(filePath, JSON.stringify({ jira_server: "invalid", jira_token: "" }));

    await expect(loadConfig(filePath)).rejects.toThrow();
  });
});
