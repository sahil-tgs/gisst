import { callClaude } from "./claude.ts";

interface QueuedMessage {
  userId: string;
  text: string;
  userName: string;
  botUsername?: string;
  onResponse: (response: string) => Promise<void>;
}

// Per-user queues — prevents concurrent Claude calls to same session
const queues = new Map<string, QueuedMessage[]>();
const processing = new Set<string>();

/**
 * Enqueue a message for agent processing.
 * Messages from the same user are processed sequentially.
 * Different users process in parallel.
 */
export async function enqueue(
  userId: string,
  text: string,
  userName: string,
  onResponse: (response: string) => Promise<void>,
  botUsername?: string
): Promise<void> {
  const msg: QueuedMessage = { userId, text, userName, botUsername, onResponse };

  if (!queues.has(userId)) {
    queues.set(userId, []);
  }
  queues.get(userId)!.push(msg);

  // If already processing for this user, the queue loop will pick it up
  if (processing.has(userId)) return;

  // Start processing
  processing.add(userId);
  await processQueue(userId);
}

async function processQueue(userId: string) {
  const queue = queues.get(userId);
  if (!queue) {
    processing.delete(userId);
    return;
  }

  while (queue.length > 0) {
    const msg = queue.shift()!;

    try {
      console.log(`[queue] Processing for ${msg.userName} (${msg.userId}): ${msg.text.slice(0, 80)}`);

      const result = await callClaude(msg.userId, msg.text, {
        userName: msg.userName,
        userPhone: msg.userId,
        botUsername: msg.botUsername,
      });

      // TODO: handle result.notionSync when Notion integration is built

      await msg.onResponse(result.text);
    } catch (err) {
      console.error(`[queue] Error for ${msg.userId}:`, err);
      try {
        await msg.onResponse("Sorry, I encountered an error. Please try again.");
      } catch {}
    }
  }

  processing.delete(userId);
  queues.delete(userId);
}
