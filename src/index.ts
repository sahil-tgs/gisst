import { config, ensureDataDirs } from "./config.ts";
import { startWhatsApp } from "./whatsapp/client.ts";

ensureDataDirs();

console.log("Gisst — Starting up...");
console.log(`Model: ${config.agent.model}`);
console.log("---");

// Start WhatsApp (Baileys — scan QR on first run)
await startWhatsApp();

// Health check server (for monitoring)
Bun.serve({
  port: config.server.port,
  fetch(req) {
    const url = new URL(req.url);
    if (url.pathname === "/health") {
      return new Response("ok", { status: 200 });
    }
    return new Response("Gisst is running. WhatsApp connected via Baileys.", { status: 200 });
  },
});

console.log(`Health check on http://0.0.0.0:${config.server.port}/health`);

// Keep alive
process.on("SIGINT", () => {
  console.log("\nShutting down Gisst...");
  process.exit(0);
});
