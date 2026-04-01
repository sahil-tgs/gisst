import { config, ensureDataDirs } from "./config.ts";
import { startTelegram, sendTextToChat } from "./telegram/client.ts";
import { startScheduler } from "./scheduler/index.ts";
import { setupNotionDatabases, getNotionDatabaseIds } from "./notion/schema.ts";

ensureDataDirs();

console.log("Gisst — Starting up...");
console.log(`Model: ${config.agent.model}`);
console.log("---");

// Auto-setup Notion databases if configured but not yet created
if (config.notion.apiKey && config.notion.pageId) {
  const existing = await getNotionDatabaseIds();
  if (!existing) {
    console.log("[notion] Setting up databases...");
    await setupNotionDatabases(config.notion.pageId);
  } else {
    console.log("[notion] Connected");
  }
} else {
  console.log("[notion] Not configured — set NOTION_API_KEY and NOTION_PAGE_ID in .env");
}

await startTelegram();

// Start the scheduler — it sends digests via Telegram
startScheduler(sendTextToChat);

process.on("SIGINT", () => {
  console.log("\nShutting down Gisst...");
  process.exit(0);
});
