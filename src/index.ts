import { config, ensureDataDirs } from "./config.ts";
import { startTelegram, sendTextToChat } from "./telegram/client.ts";
import { startScheduler } from "./scheduler/index.ts";

ensureDataDirs();

console.log("Gisst — Starting up...");
console.log(`Model: ${config.agent.model}`);
console.log("---");

await startTelegram();

// Start the scheduler — it sends digests via Telegram
startScheduler(sendTextToChat);

process.on("SIGINT", () => {
  console.log("\nShutting down Gisst...");
  process.exit(0);
});
