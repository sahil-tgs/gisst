import { Bot, Context } from "grammy";
import { config } from "../config.ts";
import { enqueue } from "../agent/queue.ts";
import { readJsonFile, writeJsonFile } from "../utils/fs.ts";
import { join } from "path";
import { addJob, loadJobs, removeJob, toggleJob, type ScheduleJobWithMeta } from "../scheduler/jobs.ts";

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

  // /schedule command — create a scheduled research job
  // Usage: /schedule "F1 News" daily 8pm
  // Usage: /schedule "AI Policy" every 4h digest 20:00
  bot.command("schedule", async (ctx) => {
    const args = ctx.match?.trim();
    if (!args) {
      await ctx.reply(
        "Usage: /schedule <topic> [cadence] [digest time]\n\n" +
        "Examples:\n" +
        '  /schedule F1 News\n' +
        '  /schedule AI Policy every 2h digest 20:00\n' +
        '  /schedule Climate Tech every 6h digest 09:00\n\n' +
        "Defaults: crawl every 4h, digest at 20:00"
      );
      return;
    }

    // Parse: topic is everything before "every" or "digest", or the whole string
    let topic = args;
    let cadence = "every 4h";
    let digestTime = "20:00";

    const everyMatch = args.match(/every\s+\d+\s*[hm]/i);
    const digestMatch = args.match(/digest\s+(\d{1,2}:\d{2})/i);

    if (everyMatch) {
      cadence = everyMatch[0];
      topic = args.slice(0, args.indexOf(everyMatch[0])).trim();
    }
    if (digestMatch) {
      digestTime = digestMatch[1];
      if (!everyMatch) {
        topic = args.slice(0, args.indexOf(digestMatch[0])).trim();
      }
    }
    if (!topic) topic = args.split(/\s+every\s+|\s+digest\s+/i)[0].trim();

    const job: ScheduleJobWithMeta = {
      id: crypto.randomUUID(),
      topic,
      keywords: topic.split(/\s+/),
      cadence,
      digestTime,
      digestTimezone: "UTC",
      lookbackWindow: "24h",
      platformPriority: [],
      active: true,
      chatId: String(ctx.chat.id),
      createdBy: String(ctx.from.id),
    };

    await addJob(job);
    await ctx.reply(
      `✅ Scheduled: "${topic}"\n\n` +
      `• Crawl: ${cadence}\n` +
      `• Digest: daily at ${digestTime} UTC\n` +
      `• ID: ${job.id.slice(0, 8)}\n\n` +
      `I'll research this topic throughout the day and send you a summary at ${digestTime}.`
    );
  });

  // /schedules command — list all scheduled jobs
  bot.command("schedules", async (ctx) => {
    const jobs = await loadJobs();
    const chatJobs = jobs.filter((j) => j.chatId === String(ctx.chat.id));

    if (chatJobs.length === 0) {
      await ctx.reply("No scheduled jobs for this chat. Create one with /schedule");
      return;
    }

    const lines = chatJobs.map((j, i) => {
      const status = j.active ? "🟢" : "⏸️";
      return `${status} ${i + 1}. "${j.topic}" — ${j.cadence}, digest at ${j.digestTime}\n   ID: ${j.id.slice(0, 8)}`;
    });

    await ctx.reply(`Scheduled jobs:\n\n${lines.join("\n\n")}\n\nCommands: /pause <id> · /remove <id>`);
  });

  // /pause command — toggle a job active/paused
  bot.command("pause", async (ctx) => {
    const idPrefix = ctx.match?.trim();
    if (!idPrefix) {
      await ctx.reply("Usage: /pause <job-id>");
      return;
    }
    const jobs = await loadJobs();
    const job = jobs.find((j) => j.id.startsWith(idPrefix));
    if (!job) {
      await ctx.reply(`No job found with ID starting with "${idPrefix}"`);
      return;
    }
    const updated = await toggleJob(job.id);
    await ctx.reply(`${updated?.active ? "▶️ Resumed" : "⏸️ Paused"}: "${job.topic}"`);
  });

  // /remove command — delete a scheduled job
  bot.command("remove", async (ctx) => {
    const idPrefix = ctx.match?.trim();
    if (!idPrefix) {
      await ctx.reply("Usage: /remove <job-id>");
      return;
    }
    const jobs = await loadJobs();
    const job = jobs.find((j) => j.id.startsWith(idPrefix));
    if (!job) {
      await ctx.reply(`No job found with ID starting with "${idPrefix}"`);
      return;
    }
    await removeJob(job.id);
    await ctx.reply(`🗑️ Removed: "${job.topic}"`);
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
    if (text.startsWith("/")) return;

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

  // Start polling (don't await — it blocks forever)
  bot.start({
    onStart: (botInfo) => {
      console.log(`[telegram] Bot started: @${botInfo.username}`);
      console.log(`[telegram] Add to a group, then send /register to activate`);
    },
  });

  // Wait for bot info to be available
  await bot.init();
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

/**
 * Send a message to a chat by ID. Used by the scheduler for digests.
 */
export async function sendTextToChat(chatId: string, text: string): Promise<void> {
  if (!bot) throw new Error("Bot not started");
  const chunks = splitMessage(text, 4000);
  for (const chunk of chunks) {
    try {
      await bot.api.sendMessage(chatId, chunk, { parse_mode: "Markdown" });
    } catch {
      await bot.api.sendMessage(chatId, chunk);
    }
  }
}

export function getBot(): Bot | null {
  return bot;
}
