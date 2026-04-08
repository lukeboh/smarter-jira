import { loadConfig, BatchProcessor } from "@core/index";

chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (message.type === "run-import") {
    handleImport(message.payload)
      .then((result) => sendResponse({ ok: true, result }))
      .catch((error: unknown) => sendResponse({ ok: false, error: String(error) }));
    return true;
  }
  return false;
});

interface ImportPayload {
  configPath: string;
  csvContent: string;
  action: "create" | "delete" | "update";
}

async function handleImport(payload: ImportPayload) {
  const config = await loadConfig(payload.configPath);
  const processor = new BatchProcessor(config);
  // TODO: converter payload.csvContent em CSV armazenado via storage API
  console.log("Executando import", payload.action);
  return { processed: 0 };
}
