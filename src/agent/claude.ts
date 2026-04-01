import { spawn } from "child_process";
import { config } from "../config.ts";
import { readJsonFile, writeJsonFile } from "../utils/fs.ts";
import { join } from "path";
import { loadAgentConfig } from "./agent-config.ts";
import { buildSystemPrompt } from "./prompt.ts";

const SESSIONS_FILE = join(config.agent.sessionDir, "sessions.json");

export interface ClaudeResponse {
  text: string;
  notionSync?: NotionSyncPayload;
}

export interface NotionSyncPayload {
  title: string;
  topic: string;
  summary: string;
  keyFindings: string[];
  sources: { title: string; url: string }[];
  tags: string[];
}

// Simple session store: userId -> sessionId
async function getSessions(): Promise<Record<string, string>> {
  return (await readJsonFile<Record<string, string>>(SESSIONS_FILE)) || {};
}

async function saveSession(userId: string, sessionId: string): Promise<void> {
  const sessions = await getSessions();
  sessions[userId] = sessionId;
  await writeJsonFile(SESSIONS_FILE, sessions);
}

/**
 * Parse the SAVE_TO_NOTION marker from agent output.
 */
function parseNotionMarker(text: string): { cleanText: string; notionSync?: NotionSyncPayload } {
  const startTag = "[SAVE_TO_NOTION:";
  const startIdx = text.indexOf(startTag);
  if (startIdx === -1) return { cleanText: text };

  const jsonStart = text.indexOf("{", startIdx);
  if (jsonStart === -1) return { cleanText: text };

  let depth = 0;
  let jsonEnd = -1;
  for (let i = jsonStart; i < text.length; i++) {
    if (text[i] === "{") depth++;
    else if (text[i] === "}") {
      depth--;
      if (depth === 0) {
        jsonEnd = i + 1;
        break;
      }
    }
  }

  if (jsonEnd === -1) return { cleanText: text };

  const closingBracket = text.indexOf("]", jsonEnd);
  const fullMarker = text.slice(startIdx, closingBracket !== -1 ? closingBracket + 1 : jsonEnd);

  try {
    const payload = JSON.parse(text.slice(jsonStart, jsonEnd)) as NotionSyncPayload;
    const cleanText = text.replace(fullMarker, "").trim();
    return { cleanText, notionSync: payload };
  } catch {
    console.warn("[claude] Failed to parse SAVE_TO_NOTION JSON");
    return { cleanText: text };
  }
}

/**
 * Call Claude Code CLI — same pattern as the working Discord bot.
 * Uses --resume (not --session-id), --output-format json, space-separated tools.
 */
export async function callClaude(
  userId: string,
  message: string,
  context?: { userName?: string; userPhone?: string; botUsername?: string }
): Promise<ClaudeResponse> {
  const sessions = await getSessions();
  const sessionId = sessions[userId];

  // Build system prompt
  const agentConfig = await loadAgentConfig("default");
  const systemPrompt = buildSystemPrompt(
    agentConfig || {
      id: "default",
      createdAt: "",
      updatedAt: "",
      identity: { name: "Scout", tone: "professional", language: "en", emojiStyle: true },
      research: { depth: "standard", topics: [], sourcePreferences: ["all"], platformPriority: [], autoCite: "footnote" },
      interaction: { responseLength: "standard", followUp: true, autoSave: true, triggerMode: "command" },
      schedule: { jobs: [], maxJobsPerDay: 20, quietHours: { start: "23:00", end: "06:00" }, defaultDigestTime: "20:00", defaultTimezone: "UTC" },
    },
    {
      userName: context?.userName,
      userPhone: context?.userPhone,
      currentDate: new Date().toISOString().split("T")[0],
      botUsername: context?.botUsername,
    }
  );

  // Build command — matches the working Discord bot pattern
  const cmd = [
    "claude",
    "-p", message,
    "--output-format", "json",
    "--model", config.agent.model,
    "--system-prompt", systemPrompt,
    "--dangerously-skip-permissions",
  ];

  // Resume existing session or let Claude create a new one
  if (sessionId) {
    cmd.push("--resume", sessionId);
  }

  const result = await spawnClaude(cmd);

  // Parse JSON response (same as Discord bot)
  try {
    const data = JSON.parse(result);
    const newSessionId = data.session_id;

    // Save session on first call (same pattern as Discord bot)
    if (newSessionId && !sessionId) {
      await saveSession(userId, newSessionId);
      console.log(`[claude] New session for ${userId}: ${newSessionId}`);
    }

    const responseText = data.result || "";
    const { cleanText, notionSync } = parseNotionMarker(responseText);
    return { text: cleanText, notionSync };
  } catch {
    // If JSON parse fails, treat as plain text
    const { cleanText, notionSync } = parseNotionMarker(result);
    return { text: cleanText, notionSync };
  }
}

/**
 * Call Claude for a Watchout Protocol background crawl (no session).
 */
export async function callClaudeHeadless(prompt: string): Promise<string> {
  const cmd = [
    "claude",
    "-p", prompt,
    "--output-format", "text",
    "--model", config.agent.model,
    "--dangerously-skip-permissions",
  ];

  return spawnClaude(cmd);
}

/**
 * Spawn a Claude CLI process and collect output.
 */
function spawnClaude(cmd: string[]): Promise<string> {
  const [binary, ...args] = cmd;

  console.log(`[claude] Spawning: ${binary} ${args.slice(0, 6).join(" ")} ... (${args.length} args)`);

  return new Promise((resolve, reject) => {
    const proc = spawn(binary, args, {
      cwd: config.agent.workDir,
      env: { ...process.env, PATH: `${process.env.HOME}/.bun/bin:${process.env.PATH}` },
      stdio: ["ignore", "pipe", "pipe"],
      timeout: config.agent.timeout,
    });

    let stdout = "";
    let stderr = "";

    proc.stdout.on("data", (data: Buffer) => {
      stdout += data.toString();
    });

    proc.stderr.on("data", (data: Buffer) => {
      stderr += data.toString();
    });

    proc.on("close", (code: number | null) => {
      console.log(`[claude] Process exited with code ${code}`);
      if (stderr) console.log(`[claude] stderr: ${stderr.slice(0, 200)}`);
      if (code === 0 && stdout.trim()) {
        resolve(stdout.trim());
      } else {
        reject(new Error(`Claude exited with code ${code}: ${stderr || stdout}`));
      }
    });

    proc.on("error", (err: Error) => {
      reject(err);
    });
  });
}

/**
 * Reset a user's session.
 */
export async function resetSession(userId: string): Promise<void> {
  const sessions = await getSessions();
  delete sessions[userId];
  await writeJsonFile(SESSIONS_FILE, sessions);
  console.log(`[claude] Session reset for ${userId}`);
}
