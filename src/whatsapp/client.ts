import makeWASocket, {
  useMultiFileAuthState,
  DisconnectReason,
  makeInMemoryStore,
  type WASocket,
} from "@whiskeysockets/baileys";
import { join } from "path";
import { config } from "../config.ts";
import { enqueue } from "../agent/queue.ts";

const AUTH_DIR = join(config.agent.sessionDir, "whatsapp-auth");
const ALLOWED_GROUPS_FILE = join(config.agent.configDir, "allowed-groups.json");

let sock: WASocket | null = null;
const store = makeInMemoryStore({});

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

async function shouldRespond(jid: string, text: string, isGroup: boolean): Promise<boolean> {
  if (!isGroup) return true;

  const allowed = await getAllowedGroups();
  if (!allowed.has(jid)) return false;

  const triggerPatterns = [
    /^!/,
    /\bscout\b/i,
    /\bgisst\b/i,
  ];

  return triggerPatterns.some((p) => p.test(text));
}

export async function startWhatsApp() {
  const { state, saveCreds } = await useMultiFileAuthState(AUTH_DIR);

  sock = makeWASocket({
    auth: state,
    printQRInTerminal: true,
  });

  store.bind(sock.ev);

  sock.ev.on("connection.update", async (update) => {
    const { connection, lastDisconnect } = update;

    if (connection === "close") {
      const statusCode = (lastDisconnect?.error as any)?.output?.statusCode;
      const shouldReconnect = statusCode !== DisconnectReason.loggedOut;

      console.log(`[whatsapp] Connection closed. Status: ${statusCode}. Reconnecting: ${shouldReconnect}`);

      if (shouldReconnect) {
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

  sock.ev.on("creds.update", saveCreds);

  sock.ev.on("messages.upsert", async ({ messages, type }) => {
    if (type !== "notify") return;

    for (const msg of messages) {
      if (msg.key.fromMe) continue;

      const text =
        msg.message?.conversation ||
        msg.message?.extendedTextMessage?.text;
      if (!text) continue;

      const chatJid = msg.key.remoteJid!;
      const isGroup = chatJid.endsWith("@g.us");
      const sender = msg.key.participant || chatJid;
      const pushName = msg.pushName || sender;
      const messageId = msg.key.id!;

      if (text.trim() === "!register" && isGroup) {
        await addAllowedGroup(chatJid);
        await sendText(chatJid, "✅ Gisst activated in this group!\n\nI'll respond to:\n• Messages starting with !\n• Messages mentioning *Scout* or *Gisst*\n\nTry: *!help* to see what I can do.");
        continue;
      }

      if (!(await shouldRespond(chatJid, text, isGroup))) continue;

      console.log(`[whatsapp] ${pushName} (${sender}): ${text.slice(0, 100)}`);

      await reactToMessage(chatJid, messageId, "🔍");

      await enqueue(sender, text, pushName, async (response) => {
        await reactToMessage(chatJid, messageId, "✅");
        await sendText(chatJid, response);
      });
    }
  });

  return sock;
}

export async function sendText(jid: string, text: string): Promise<void> {
  if (!sock) throw new Error("WhatsApp not connected");

  const chunks = splitMessage(text, 4000);
  for (const chunk of chunks) {
    await sock.sendMessage(jid, { text: chunk });
  }
}

export async function reactToMessage(jid: string, messageId: string, emoji: string): Promise<void> {
  if (!sock) return;
  try {
    await sock.sendMessage(jid, {
      react: { text: emoji, key: { remoteJid: jid, id: messageId } },
    });
  } catch {}
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

export function getSocket(): WASocket | null {
  return sock;
}
