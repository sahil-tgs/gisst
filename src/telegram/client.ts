import { Bot, Context } from "grammy";
import { config } from "../config.ts";
import { enqueue } from "../agent/queue.ts";
import { readJsonFile, writeJsonFile } from "../utils/fs.ts";
import { join } from "path";

const ALLOWED_GROUPS_FILE = join(config.agent.configDir, "allowed-groups.json");

let bot: Bot | null = null;

async function getAllowedGroups(): Promise<Set<string>> {
  const data = await readJsonFile<string[]>(ALLOWED_GROUPS_FILE);
  return new Set(data || []);
}

async function addAllowedGroup(id: string): Promise<void> {
  const groups = await getAllowedGroups();
  groups.add(id);
  await writeJsonFile(ALLOWED_GROUPS_FILE, [...groups]);
  console.log(`[telegram] Group registered: ${id}`);
}

async function shouldRespond(chatId: string, text: string, isGroup: boolean): Promise<boolean> {
  if (!isGroup) return true;

  const allowed = await getAllowedGroups();
  if (!allowed.has(chatId)) return false;

  const triggerPatterns = [
    /^!/,
    /\bscout\b/i,
    /\bgisst\b/i,
  ];

  return triggerPatterns.some((p) => p.test(text));
}

export async function startTelegram() {
  const token = config.telegram.botToken;
  if (!token) {
    console.error("[telegram] TELEGRAM_BOT_TOKEN not set in .env");
    process.exit(1);
  }

  bot = new Bot(token);

  // /start command
  bot.command("start", async (ctx) => {
    await ctx.reply(
      "👋 I'm Scout, your Gisst research agent.\n\n" +
      "Ask me anything — I'll search the web and give you cited answers.\n\n" +
      "In groups: add me, then send /register to activate."
    );
  });

  // /register command — activate bot in this group
  bot.command("register", async (ctx) => {
    if (ctx.chat.type === "private") {
      await ctx.reply("This command is for groups. Just DM me directly!");
      return;
    }

    await addAllowedGroup(String(ctx.chat.id));
    await ctx.reply(
      "✅ Gisst activated in this group!\n\n" +
      "I'll respond to:\n" +
      "• Messages starting with !\n" +
      "• Messages mentioning Scout or Gisst\n" +
      "• Direct replies to my messages\n\n" +
      "Try: !help to see what I can do."
    );
  });

  // Handle all text messages
  bot.on("message:text", async (ctx) => {
    const text = ctx.message.text;
    const chatId = String(ctx.chat.id);
    const isGroup = ctx.chat.type === "group" || ctx.chat.type === "supergroup";
    const sender = String(ctx.from.id);
    const pushName = ctx.from.first_name + (ctx.from.last_name ? ` ${ctx.from.last_name}` : "");

    // Check if bot was mentioned via @username or replied to
    const botMentioned = ctx.message.entities?.some(
      (e) => e.type === "mention" && text.slice(e.offset, e.offset + e.length) === `@${bot!.botInfo.username}`
    );
    const isReplyToBot = ctx.message.reply_to_message?.from?.id === bot!.botInfo.id;

    // In groups, also respond to @mentions and replies
    if (isGroup && !botMentioned && !isReplyToBot && !(await shouldRespond(chatId, text, isGroup))) {
      return;
    }

    // Skip commands handled elsewhere
    if (text.startsWith("/register") || text.startsWith("/start")) return;

    console.log(`[telegram] ${pushName} (${sender}): ${text.slice(0, 100)}`);

    // Show typing indicator
    await ctx.replyWithChatAction("typing");

    // Keep typing indicator alive during processing
    const typingInterval = setInterval(() => {
      ctx.replyWithChatAction("typing").catch(() => {});
    }, 4000);

    await enqueue(sender, text, pushName, async (response) => {
      clearInterval(typingInterval);

      const chunks = splitMessage(response, 4000);
      for (const chunk of chunks) {
        try {
          await ctx.reply(chunk, {
            reply_to_message_id: ctx.message.message_id,
            parse_mode: "Markdown",
          });
        } catch {
          // Fallback to plain text if Markdown parsing fails
          await ctx.reply(chunk, {
            reply_to_message_id: ctx.message.message_id,
          });
        }
      }
    }, bot!.botInfo.username);
  });

  // Error handler
  bot.catch((err) => {
    console.error("[telegram] Bot error:", err);
  });

  // Start polling
  await bot.start({
    onStart: (botInfo) => {
      console.log(`[telegram] Bot started: @${botInfo.username}`);
      console.log(`[telegram] Add to a group, then send /register to activate`);
    },
  });
}

function splitMessage(text: string, maxLength: number): string[] {
  if (text.length <= maxLength) return [text];

  const chunks: string[] = [];
  let remaining = text;

  while (remaining.length > 0) {
    if (remaining.length <= maxLength) {
      chunks.push(remaining);
      break;
    }

    let splitIdx = remaining.lastIndexOf("\n\n", maxLength);
    if (splitIdx === -1 || splitIdx < maxLength / 2) {
      splitIdx = remaining.lastIndexOf("\n", maxLength);
    }
    if (splitIdx === -1 || splitIdx < maxLength / 2) {
      splitIdx = remaining.lastIndexOf(" ", maxLength);
    }
    if (splitIdx === -1 || splitIdx < maxLength / 2) {
      splitIdx = maxLength;
    }

    chunks.push(remaining.slice(0, splitIdx));
    remaining = remaining.slice(splitIdx).trimStart();
  }

  return chunks;
}

export function getBot(): Bot | null {
  return bot;
}
