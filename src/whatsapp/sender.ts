import { config } from "../config.ts";

const API_BASE = `https://graph.facebook.com/v21.0/${config.whatsapp.phoneNumberId}`;

async function whatsappApi(endpoint: string, body: Record<string, unknown>) {
  const res = await fetch(`${API_BASE}${endpoint}`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${config.whatsapp.accessToken}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify(body),
  });

  if (!res.ok) {
    const err = await res.text();
    console.error(`[whatsapp] API error ${res.status}:`, err);
  }

  return res;
}

/**
 * Send a text message. Splits at 4000 chars on paragraph boundaries.
 */
export async function sendText(to: string, text: string): Promise<void> {
  const chunks = splitMessage(text, 4000);
  for (const chunk of chunks) {
    await whatsappApi("/messages", {
      messaging_product: "whatsapp",
      to,
      type: "text",
      text: { body: chunk },
    });
  }
}

/**
 * React to a message with an emoji.
 */
export async function sendReaction(to: string, messageId: string, emoji: string): Promise<void> {
  await whatsappApi("/messages", {
    messaging_product: "whatsapp",
    to,
    type: "reaction",
    reaction: { message_id: messageId, emoji },
  });
}

/**
 * Mark a message as read (shows blue ticks).
 */
export async function markAsRead(messageId: string): Promise<void> {
  await whatsappApi("/messages", {
    messaging_product: "whatsapp",
    status: "read",
    message_id: messageId,
  });
}

/**
 * Split long text at paragraph boundaries.
 */
function splitMessage(text: string, maxLength: number): string[] {
  if (text.length <= maxLength) return [text];

  const chunks: string[] = [];
  let remaining = text;

  while (remaining.length > 0) {
    if (remaining.length <= maxLength) {
      chunks.push(remaining);
      break;
    }

    // Try to split at double newline (paragraph)
    let splitIdx = remaining.lastIndexOf("\n\n", maxLength);
    if (splitIdx === -1 || splitIdx < maxLength / 2) {
      // Try single newline
      splitIdx = remaining.lastIndexOf("\n", maxLength);
    }
    if (splitIdx === -1 || splitIdx < maxLength / 2) {
      // Try space
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
