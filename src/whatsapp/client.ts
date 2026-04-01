import makeWASocket, {
  useMultiFileAuthState,
  DisconnectReason,
  type WASocket,
} from "@whiskeysockets/baileys";
import { join } from "path";
import { config } from "../config.ts";
import { enqueue } from "../agent/queue.ts";

const AUTH_DIR = join(config.agent.sessionDir, "whatsapp-auth");
const ALLOWED_GROUPS_FILE = join(config.agent.configDir, "allowed-groups.json");

let sock: WASocket | null = null;

/**
 * Load allowed group JIDs. If empty, bot responds nowhere (safe default).
 * Add groups via !register command or manually in allowed-groups.json.
 */
async function getAllowedGroups(): Promise<Set<string>> {
  try {
    const file = Bun.file(ALLOWED_GROUPS_FILE);
    if (await file.exists()) {
      const data: string[] = await file.json();
      return new Set(data);
    }
  } catch {}
  return new Set();
}

async function addAllowedGroup(jid: string): Promise<void> {
  const groups = await getAllowedGroups();
  groups.add(jid);
  await Bun.write(ALLOWED_GROUPS_FILE, JSON.stringify([...groups], null, 2));
  console.log(`[whatsapp] Group registered: ${jid}`);
}

/**
 * Check if the bot should respond to a message.
 */
async function shouldRespond(jid: string, text: string, isGroup: boolean): Promise<boolean> {
  // DMs: always respond
  if (!isGroup) return true;

  // Groups: only respond if group is registered
  const allowed = await getAllowedGroups();
  if (!allowed.has(jid)) return false;

  // In allowed groups, respond to !commands or when bot name is mentioned
  const triggerPatterns = [
    /^!/,                    // !commands
    /\bscout\b/i,           // default agent name mention
    /\bgisst\b/i,           // product name mention
  ];

  return triggerPatterns.some((p) => p.test(text));
}

/**
 * Start the WhatsApp client via Baileys.
 * First run: prints QR code in terminal — scan with your phone.
 * Subsequent runs: reconnects automatically using saved auth state.
 */
export async function startWhatsApp() {
  const { state, saveCreds } = await useMultiFileAuthState(AUTH_DIR);

  sock = makeWASocket({
    auth: state,
    // v7: QR is handled via connection.update event, not printQRInTerminal
  });

  // Handle connection updates
  sock.ev.on("connection.update", async (update) => {
    const { connection, lastDisconnect, qr } = update;

    // QR code available — print it for scanning
    if (qr) {
      // Dynamic import to avoid issues if not installed
      try {
        const { default: qrcode } = await import("qrcode-terminal");
        qrcode.generate(qr, { small: true });
        console.log("\n[whatsapp] ^^^^ Scan this QR code with WhatsApp ^^^^\n");
      } catch {
        // Fallback: just print the raw QR string
        console.log("\n[whatsapp] QR Code (scan with WhatsApp):");
        console.log(qr);
        console.log("\nInstall qrcode-terminal for a scannable QR: bun add qrcode-terminal\n");
      }
    }

    if (connection === "close") {
      const statusCode = (lastDisconnect?.error as any)?.output?.statusCode;
      const shouldReconnect = statusCode !== DisconnectReason.loggedOut;

      console.log(`[whatsapp] Connection closed. Status: ${statusCode}. Reconnecting: ${shouldReconnect}`);

      if (shouldReconnect) {
        // Delay before reconnect to prevent infinite rapid loop
        await new Promise((r) => setTimeout(r, 3000));
        startWhatsApp();
      } else {
        console.log("[whatsapp] Logged out. Delete data/sessions/whatsapp-auth and restart.");
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

      const chatJid = msg.key.remoteJid!;
      const isGroup = chatJid.endsWith("@g.us");
      const sender = msg.key.participant || chatJid;
      const pushName = msg.pushName || sender;
      const messageId = msg.key.id!;

      // Handle !register command — adds this group to allowed list
      if (text.trim() === "!register" && isGroup) {
        await addAllowedGroup(chatJid);
        await sendText(chatJid, "✅ Gisst activated in this group!\n\nI'll respond to:\n• Messages starting with !\n• Messages mentioning *Scout* or *Gisst*\n\nTry: *!help* to see what I can do.");
        continue;
      }

      // Check if bot should respond
      if (!(await shouldRespond(chatJid, text, isGroup))) continue;

      console.log(`[whatsapp] ${pushName} (${sender}): ${text.slice(0, 100)}`);

      // React with 🔍
      await reactToMessage(chatJid, messageId, "🔍");

      // Enqueue for agent processing
      await enqueue(sender, text, pushName, async (response) => {
        // React with ✅
        await reactToMessage(chatJid, messageId, "✅");

        // Send response to the chat
        await sendText(chatJid, response);
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
