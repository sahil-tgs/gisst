import { spawn } from "child_process";
import { config } from "../config.ts";
import { getSession, createSession, updateSession, deleteSession } from "./sessions.ts";
import { loadAgentConfig } from "./agent-config.ts";
import { buildSystemPrompt } from "./prompt.ts";

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

/**
 * Parse the SAVE_TO_NOTION marker from agent output.
 * Returns clean text (marker removed) and the parsed payload if found.
 */
function parseNotionMarker(text: string): { cleanText: string; notionSync?: NotionSyncPayload } {
  const marker = /\[SAVE_TO_NOTION:\s*(\{[\s\S]*?\})\]/;
  const match = text.match(marker);

  if (!match) return { cleanText: text };

  try {
    const payload = JSON.parse(match[1]) as NotionSyncPayload;
    const cleanText = text.replace(marker, "").trim();
    return { cleanText, notionSync: payload };
  } catch {
    console.warn("[claude] Failed to parse SAVE_TO_NOTION marker:", match[1]);
    return { cleanText: text };
  }
}

/**
 * Call Claude Code CLI with a message.
 */
export async function callClaude(
  userId: string,
  message: string,
  context?: { userName?: string; userPhone?: string }
): Promise<ClaudeResponse> {
  // Get or create session
  let session = await getSession(userId);
  const agentId = session?.agentId || "default";

  // Load agent config (or use null for unconfigured agent)
  const agentConfig = await loadAgentConfig(agentId);

  if (!session) {
    session = await createSession(userId, agentId);
  }

  // Build system prompt
  const systemPrompt = agentConfig
    ? buildSystemPrompt(agentConfig, {
        userName: context?.userName,
        userPhone: context?.userPhone,
        currentDate: new Date().toISOString().split("T")[0],
      })
    : buildSystemPrompt(
        // Minimal default config when no agent is configured yet
        {
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
        }
      );

  const args = [
    "-p",
    "--output-format", "text",
    "--model", config.agent.model,
    "--system-prompt", systemPrompt,
    "--session-id", session.sessionId,
    "--allowedTools", "WebSearch,WebFetch,Read,Write,Bash",
    message,
  ];

  const result = await spawnClaude(args);

  // Update session metadata
  await updateSession(userId, {
    lastActive: new Date().toISOString(),
    messageCount: session.messageCount + 1,
  });

  // Parse for Notion sync markers
  const { cleanText, notionSync } = parseNotionMarker(result);

  return { text: cleanText, notionSync };
}

/**
 * Call Claude for a Watchout Protocol background crawl (no session, no user context).
 */
export async function callClaudeHeadless(prompt: string): Promise<string> {
  const args = [
    "-p",
    "--output-format", "text",
    "--model", config.agent.model,
    "--allowedTools", "WebSearch,WebFetch",
    prompt,
  ];

  return spawnClaude(args);
}

/**
 * Spawn a Claude CLI process and collect output.
 */
function spawnClaude(args: string[]): Promise<string> {
  return new Promise((resolve, reject) => {
    const proc = spawn("claude", args, {
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
      if (code === 0 && stdout.trim()) {
        resolve(stdout.trim());
      } else if (stderr.includes("context") || stderr.includes("limit")) {
        console.log("[claude] Context limit hit. Initiating rebirth...");
        // Return what we have, caller should handle rebirth
        resolve(stdout.trim() || "[Session context limit reached. Starting fresh session.]");
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
 * Reset a user's session (rebirth).
 */
export async function resetSession(userId: string): Promise<void> {
  await deleteSession(userId);
  console.log(`[claude] Session reset for user ${userId}. New session on next message.`);
}
