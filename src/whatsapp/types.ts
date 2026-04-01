// WhatsApp Cloud API webhook payload types
// Docs: https://developers.facebook.com/docs/whatsapp/cloud-api/webhooks/components

export interface WebhookPayload {
  object: "whatsapp_business_account";
  entry: WebhookEntry[];
}

export interface WebhookEntry {
  id: string;
  changes: WebhookChange[];
}

export interface WebhookChange {
  value: {
    messaging_product: "whatsapp";
    metadata: {
      display_phone_number: string;
      phone_number_id: string;
    };
    contacts?: WebhookContact[];
    messages?: WebhookMessage[];
    statuses?: WebhookStatus[];
  };
  field: "messages";
}

export interface WebhookContact {
  profile: { name: string };
  wa_id: string;
}

export interface WebhookMessage {
  from: string;
  id: string;
  timestamp: string;
  type: "text" | "image" | "audio" | "video" | "document" | "reaction" | "interactive";
  text?: { body: string };
  image?: { id: string; mime_type: string; caption?: string };
  reaction?: { message_id: string; emoji: string };
  interactive?: { type: string; button_reply?: { id: string; title: string } };
}

export interface WebhookStatus {
  id: string;
  status: "sent" | "delivered" | "read" | "failed";
  timestamp: string;
  recipient_id: string;
}

// Parsed message for internal use
export interface ParsedMessage {
  from: string;
  name: string;
  messageId: string;
  text: string;
  timestamp: string;
}

/**
 * Extract text messages from a webhook payload.
 */
export function parseWebhookMessages(payload: WebhookPayload): ParsedMessage[] {
  const messages: ParsedMessage[] = [];

  for (const entry of payload.entry) {
    for (const change of entry.changes) {
      const { contacts, messages: msgs } = change.value;
      if (!msgs || !contacts) continue;

      const contactMap = new Map(contacts.map((c) => [c.wa_id, c.profile.name]));

      for (const msg of msgs) {
        if (msg.type === "text" && msg.text?.body) {
          messages.push({
            from: msg.from,
            name: contactMap.get(msg.from) || msg.from,
            messageId: msg.id,
            text: msg.text.body,
            timestamp: msg.timestamp,
          });
        }
      }
    }
  }

  return messages;
}
