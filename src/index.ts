import { config, ensureDataDirs } from "./config.ts";
import { handleVerification, handleIncoming } from "./whatsapp/webhook.ts";

ensureDataDirs();

console.log("Gisst — Starting up...");
console.log(`Model: ${config.agent.model}`);
console.log(`Port: ${config.server.port}`);
console.log(`Webhook: ${config.server.webhookPath}`);
console.log("---");

Bun.serve({
  port: config.server.port,

  async fetch(req) {
    const url = new URL(req.url);
    const path = url.pathname;

    // Health check
    if (path === "/health") {
      return new Response("ok", { status: 200 });
    }

    // WhatsApp webhook
    if (path === config.server.webhookPath) {
      if (req.method === "GET") return handleVerification(req);
      if (req.method === "POST") return handleIncoming(req);
    }

    return new Response("Not found", { status: 404 });
  },
});

console.log(`Gisst listening on http://0.0.0.0:${config.server.port}`);
console.log(`Webhook endpoint: ${config.server.webhookPath}`);
