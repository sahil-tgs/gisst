#!/usr/bin/env bun
/**
 * CLI test harness for the Gisst agent.
 * Run: bun scripts/test-agent.ts
 *
 * Tests the agent directly — no WhatsApp needed.
 * Type messages, get responses. Uses a persistent session.
 */

import { createAgentConfig, loadAgentConfig } from "../src/agent/agent-config.ts";
import { callClaude, resetSession } from "../src/agent/claude.ts";
import { ensureDataDirs } from "../src/config.ts";

const TEST_USER = "test-cli-user";
const TEST_AGENT_ID = "test-agent";

async function setupTestAgent() {
  ensureDataDirs();

  // Create a test agent config if one doesn't exist
  let agentConfig = await loadAgentConfig(TEST_AGENT_ID);
  if (!agentConfig) {
    console.log("Creating test agent with default config...\n");
    agentConfig = await createAgentConfig({
      id: TEST_AGENT_ID,
      identity: {
        name: "Scout",
        tone: "professional",
        language: "en",
        emojiStyle: true,
      },
      research: {
        depth: "standard",
        topics: [],
        sourcePreferences: ["all"],
        platformPriority: [],
        autoCite: "footnote",
      },
    });
  }

  console.log(`Agent: ${agentConfig.identity.name} (${agentConfig.identity.tone})`);
  console.log(`Depth: ${agentConfig.research.depth}`);
  console.log(`Model: ${process.env.CLAUDE_MODEL || "claude-sonnet-4-6"}`);
  console.log("---");
  console.log("Type a message to talk to the agent.");
  console.log("Commands: !new (reset session), !config (show config), !quit (exit)");
  console.log("---\n");

  return agentConfig;
}

async function main() {
  const agentConfig = await setupTestAgent();
  const reader = Bun.stdin.stream().getReader();
  const decoder = new TextDecoder();

  process.stdout.write("You: ");

  let buffer = "";
  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });

    // Process complete lines
    while (buffer.includes("\n")) {
      const newlineIdx = buffer.indexOf("\n");
      const line = buffer.slice(0, newlineIdx).trim();
      buffer = buffer.slice(newlineIdx + 1);

      if (!line) {
        process.stdout.write("You: ");
        continue;
      }

      // Handle local commands
      if (line === "!quit" || line === "!exit") {
        console.log("Bye!");
        process.exit(0);
      }

      if (line === "!new") {
        await resetSession(TEST_USER);
        console.log("[Session reset. Fresh start.]\n");
        process.stdout.write("You: ");
        continue;
      }

      if (line === "!config") {
        console.log(JSON.stringify(agentConfig, null, 2));
        process.stdout.write("\nYou: ");
        continue;
      }

      // Send to Claude
      console.log("[Processing...]\n");
      try {
        const response = await callClaude(TEST_USER, line, {
          userName: "Test User",
        });

        console.log(`${agentConfig.identity.name}: ${response.text}\n`);

        if (response.notionSync) {
          console.log("[NOTION SYNC DETECTED]");
          console.log(`  Title: ${response.notionSync.title}`);
          console.log(`  Topic: ${response.notionSync.topic}`);
          console.log(`  Tags: ${response.notionSync.tags.join(", ")}`);
          console.log();
        }
      } catch (err) {
        console.error(`[Error: ${err instanceof Error ? err.message : err}]\n`);
      }

      process.stdout.write("You: ");
    }
  }
}

main().catch(console.error);
