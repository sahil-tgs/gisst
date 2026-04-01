import { loadJobs, updateJobTimestamp, type ScheduleJobWithMeta } from "./jobs.ts";
import { stageFinding, loadStagedFindings, clearStaging } from "./staging.ts";
import { callClaudeHeadless } from "../agent/claude.ts";
import { buildWatchoutCrawlPrompt, buildWatchoutDigestPrompt } from "../agent/prompt.ts";
import { loadAgentConfig, type AgentConfig } from "../agent/agent-config.ts";

// Callback to send a message to a Telegram chat
type SendMessageFn = (chatId: string, text: string) => Promise<void>;

let sendMessage: SendMessageFn | null = null;
let tickInterval: ReturnType<typeof setInterval> | null = null;

const TICK_INTERVAL_MS = 60_000; // Check every minute

/**
 * Parse cadence string to milliseconds.
 * Supports: "every 1h", "every 4h", "every 30m", "every 2 hours"
 */
function parseCadenceMs(cadence: string): number {
  const match = cadence.match(/(\d+)\s*(h|hr|hrs|hours?|m|min|mins|minutes?)/i);
  if (!match) return 4 * 60 * 60 * 1000; // default 4 hours
  const val = parseInt(match[1]);
  const unit = match[2].toLowerCase();
  if (unit.startsWith("h")) return val * 60 * 60 * 1000;
  if (unit.startsWith("m")) return val * 60 * 1000;
  return 4 * 60 * 60 * 1000;
}

/**
 * Parse time string "HH:MM" to { hours, minutes }
 */
function parseTime(timeStr: string): { hours: number; minutes: number } {
  const [h, m] = timeStr.split(":").map(Number);
  return { hours: h || 0, minutes: m || 0 };
}

/**
 * Check if a job's crawl is due.
 */
function isCrawlDue(job: ScheduleJobWithMeta): boolean {
  if (!job.active) return false;
  if (!job.lastCrawl) return true;

  const cadenceMs = parseCadenceMs(job.cadence);
  const elapsed = Date.now() - new Date(job.lastCrawl).getTime();
  return elapsed >= cadenceMs;
}

/**
 * Check if a job's digest is due (within the current minute of digestTime).
 */
function isDigestDue(job: ScheduleJobWithMeta): boolean {
  if (!job.active) return false;

  const now = new Date();
  const { hours, minutes } = parseTime(job.digestTime);

  // Check if current time matches digest time (within the tick window)
  if (now.getHours() !== hours || now.getMinutes() !== minutes) return false;

  // Don't send if already sent today
  if (job.lastDigest) {
    const lastDate = new Date(job.lastDigest).toISOString().split("T")[0];
    const today = now.toISOString().split("T")[0];
    if (lastDate === today) return false;
  }

  return true;
}

/**
 * Run a background crawl for a job.
 */
async function runCrawl(job: ScheduleJobWithMeta): Promise<void> {
  console.log(`[scheduler] Crawling: "${job.topic}"`);
  try {
    const prompt = buildWatchoutCrawlPrompt(job);
    const result = await callClaudeHeadless(prompt);
    await stageFinding(job.id, result);
    await updateJobTimestamp(job.id, "lastCrawl");
    console.log(`[scheduler] Crawl complete: "${job.topic}"`);
  } catch (err) {
    console.error(`[scheduler] Crawl failed for "${job.topic}":`, err);
  }
}

/**
 * Synthesize and send a digest for a job.
 */
async function runDigest(job: ScheduleJobWithMeta): Promise<void> {
  console.log(`[scheduler] Building digest: "${job.topic}"`);
  try {
    const findings = await loadStagedFindings(job.id);
    if (findings.length === 0) {
      console.log(`[scheduler] No findings for "${job.topic}", skipping digest`);
      return;
    }

    const agentConfig = await loadAgentConfig("default") as AgentConfig;
    const prompt = buildWatchoutDigestPrompt(job, agentConfig, findings);
    const digest = await callClaudeHeadless(prompt);

    // Send to Telegram
    if (sendMessage) {
      await sendMessage(job.chatId, digest);
      console.log(`[scheduler] Digest sent to chat ${job.chatId}: "${job.topic}"`);
    }

    await clearStaging(job.id);
    await updateJobTimestamp(job.id, "lastDigest");
  } catch (err) {
    console.error(`[scheduler] Digest failed for "${job.topic}":`, err);
  }
}

/**
 * Main tick — called every minute.
 */
async function tick(): Promise<void> {
  const jobs = await loadJobs();
  const activeJobs = jobs.filter((j) => j.active);

  if (activeJobs.length === 0) return;

  for (const job of activeJobs) {
    // Check for due crawls
    if (isCrawlDue(job)) {
      runCrawl(job).catch((err) => console.error(`[scheduler] Crawl error:`, err));
    }

    // Check for due digests
    if (isDigestDue(job)) {
      runDigest(job).catch((err) => console.error(`[scheduler] Digest error:`, err));
    }
  }
}

/**
 * Start the scheduler. Pass a function to send Telegram messages.
 */
export function startScheduler(messageSender: SendMessageFn): void {
  sendMessage = messageSender;

  // Run first tick immediately
  tick();

  // Then every minute
  tickInterval = setInterval(tick, TICK_INTERVAL_MS);

  console.log(`[scheduler] Started — checking every ${TICK_INTERVAL_MS / 1000}s`);
}

export function stopScheduler(): void {
  if (tickInterval) {
    clearInterval(tickInterval);
    tickInterval = null;
  }
  console.log("[scheduler] Stopped");
}
