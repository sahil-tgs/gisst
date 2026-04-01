import { config, ensureDataDirs } from "./config.ts";
import { startTelegram } from "./telegram/client.ts";

ensureDataDirs();

console.log("Gisst — Starting up...");
console.log(`Model: ${config.agent.model}`);
console.log("---");

await startTelegram();

process.on("SIGINT", () => {
  console.log("\nShutting down Gisst...");
  process.exit(0);
});
