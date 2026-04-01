import { config } from "../config.ts";
import { parseWebhookMessages, type WebhookPayload, type ParsedMessage } from "./types.ts";
import { sendReaction, sendText, markAsRead } from "./sender.ts";
import { enqueue } from "../agent/queue.ts";

/**
 * GET handler — WhatsApp webhook verification.
 * Meta sends hub.mode, hub.verify_token, hub.challenge as query params.
 */
export function handleVerification(req: Request): Response {
  const url = new URL(req.url);
  const mode = url.searchParams.get("hub.mode");
  const token = url.searchParams.get("hub.verify_token");
  const challenge = url.searchParams.get("hub.challenge");

  if (mode === "subscribe" && token === config.whatsapp.verifyToken) {
    console.log("[webhook] Verification successful");
    return new Response(challenge, { status: 200 });
  }

  console.warn("[webhook] Verification failed — token mismatch");
  return new Response("Forbidden", { status: 403 });
}

/**
 * POST handler — Incoming WhatsApp messages.
 * MUST return 200 within 5 seconds or Meta retries.
 */
export async function handleIncoming(req: Request): Promise<Response> {
  let payload: WebhookPayload;
  try {
    payload = await req.json() as WebhookPayload;
  } catch {
    return new Response("Bad Request", { status: 400 });
  }

  // Parse text messages from the webhook
  const messages = parseWebhookMessages(payload);

  if (messages.length === 0) {
    // Could be a status update, not a message — that's fine
    return new Response("OK", { status: 200 });
  }

  // Return 200 immediately — process async
  // (WhatsApp retries if we take >5s)
  for (const msg of messages) {
    processMessageAsync(msg);
  }

  return new Response("OK", { status: 200 });
}

/**
 * Process a message asynchronously after returning 200.
 */
async function processMessageAsync(msg: ParsedMessage) {
  try {
    console.log(`[webhook] ${msg.name} (${msg.from}): ${msg.text.slice(0, 100)}`);

    // Mark as read
    await markAsRead(msg.messageId);

    // React with 🔍 to show we're working on it
    await sendReaction(msg.from, msg.messageId, "🔍");

    // Enqueue for agent processing
    await enqueue(msg.from, msg.text, msg.name, async (response) => {
      // Remove search reaction, add checkmark
      await sendReaction(msg.from, msg.messageId, "✅");

      // Send response
      await sendText(msg.from, response);
    });
  } catch (err) {
    console.error(`[webhook] Error processing message from ${msg.from}:`, err);
    try {
      await sendReaction(msg.from, msg.messageId, "❌");
      await sendText(msg.from, "Sorry, I ran into an error processing your request. Try again?");
    } catch {}
  }
}
