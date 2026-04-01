import { join } from "path";

const SRC_DIR = import.meta.dir;

export const config = {
  agent: {
    workDir: process.env.GISST_WORK_DIR || join(SRC_DIR, "data", "workspace"),
    model: process.env.CLAUDE_MODEL || "claude-sonnet-4-6",
    timeout: parseInt(process.env.AGENT_TIMEOUT || "300000"),
    configDir: join(SRC_DIR, "data", "agents"),
    sessionDir: join(SRC_DIR, "data", "sessions"),
    stagingDir: join(SRC_DIR, "data", "staging"),
  },
  whatsapp: {
    verifyToken: process.env.WHATSAPP_VERIFY_TOKEN || "",
    accessToken: process.env.WHATSAPP_ACCESS_TOKEN || "",
    phoneNumberId: process.env.WHATSAPP_PHONE_NUMBER_ID || "",
  },
  notion: {
    apiKey: process.env.NOTION_API_KEY || "",
    researchDbId: process.env.NOTION_RESEARCH_DB_ID || "",
    digestDbId: process.env.NOTION_DIGEST_DB_ID || "",
  },
  server: {
    port: parseInt(process.env.PORT || "3000"),
    webhookPath: process.env.WEBHOOK_PATH || "/webhook",
  },
  srcDir: SRC_DIR,
} as const;

export function ensureDataDirs() {
  const dirs = [
    config.agent.workDir,
    config.agent.configDir,
    config.agent.sessionDir,
    config.agent.stagingDir,
  ];
  for (const dir of dirs) {
    Bun.spawnSync(["mkdir", "-p", dir]);
  }
}
