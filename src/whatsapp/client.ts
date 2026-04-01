import makeWASocket, {
  useMultiFileAuthState,
  DisconnectReason,
  makeInMemoryStore,
  type WASocket,
  type BaileysEventMap,
} from "@whiskeysockets/baileys";
import { join } from "path";
import { config } from "../config.ts";
import { enqueue } from "../agent/queue.ts";

const AUTH_DIR = join(config.agent.sessionDir, "whatsapp-auth");
const STORE_FILE = join(config.agent.sessionDir, "whatsapp-store.json");

let sock: WASocket | null = null;

/**
 * Start the WhatsApp client via Baileys.
 * First run: prints QR code in terminal — scan with your phone.
 * Subsequent runs: reconnects automatically using saved auth state.
 */
export async function startWhatsApp() {
  // Auth state persists between restarts
  const { state, saveCreds } = await useMultiFileAuthState(AUTH_DIR);

  // In-memory store for message history (optional, helps with message context)
  const store = makeInMemoryStore({});
  try {
    const storeFile = Bun.file(STORE_FILE);
    if (await storeFile.exists()) {
      store.readFromFile(STORE_FILE);
    }
  } catch {}

  // Save store periodically
  setInterval(() => {
    store.writeToFile(STORE_FILE);
  }, 30_000);

  sock = makeWASocket({
    auth: state,
    printQRInTerminal: true,
  });

  store.bind(sock.ev);

  // Handle connection updates
  sock.ev.on("connection.update", (update) => {
    const { connection, lastDisconnect, qr } = update;

    if (qr) {
      console.log("[whatsapp] Scan QR code above with your phone");
    }

    if (connection === "close") {
      const statusCode = (lastDisconnect?.error as any)?.output?.statusCode;
      const shouldReconnect = statusCode !== DisconnectReason.loggedOut;

      console.log(`[whatsapp] Connection closed. Status: ${statusCode}. Reconnecting: ${shouldReconnect}`);

      if (shouldReconnect) {
        startWhatsApp();
      } else {
        console.log("[whatsapp] Logged out. Delete auth folder and restart to re-authenticate.");
      }
    }

    if (connection === "open") {
      console.log("[whatsapp] Connected successfully!");
    }
  });

  // Save credentials on update
  sock.ev.on("creds.update", saveCreds);

  // Handle incoming messages
  sock.ev.on("messages.upsert", async ({ messages, type }) => {
    if (type !== "notify") return;

    for (const msg of messages) {
      // Skip own messages
      if (msg.key.fromMe) continue;

      // Skip non-text messages for now
      const text =
        msg.message?.conversation ||
        msg.message?.extendedTextMessage?.text;
      if (!text) continue;

      const from = msg.key.remoteJid!;
      const sender = msg.key.participant || from; // participant for group chats
      const pushName = msg.pushName || sender;
      const messageId = msg.key.id!;

      console.log(`[whatsapp] ${pushName} (${sender}): ${text.slice(0, 100)}`);

      // React with 🔍
      await reactToMessage(from, messageId, "🔍");

      // Enqueue for agent processing
      await enqueue(sender, text, pushName, async (response) => {
        // React with ✅
        await reactToMessage(from, messageId, "✅");

        // Send response to the chat (works for both DMs and groups)
        await sendText(from, response);
      });
    }
  });

  return sock;
}

/**
 * Send a text message. Splits at 4000 chars.
 */
export async function sendText(jid: string, text: string): Promise<void> {
  if (!sock) throw new Error("WhatsApp not connected");

  const chunks = splitMessage(text, 4000);
  for (const chunk of chunks) {
    await sock.sendMessage(jid, { text: chunk });
  }
}

/**
 * React to a message.
 */
export async function reactToMessage(jid: string, messageId: string, emoji: string): Promise<void> {
  if (!sock) return;
  try {
    await sock.sendMessage(jid, {
      react: { text: emoji, key: { remoteJid: jid, id: messageId } },
    });
  } catch {
    // Reactions can fail silently — not critical
  }
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

export function getSocket(): WASocket | null {
  return sock;
}
