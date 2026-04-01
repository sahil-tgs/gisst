import { join } from "path";
import { config } from "../config.ts";

export interface SessionData {
  sessionId: string;
  agentId: string;
  createdAt: string;
  lastActive: string;
  messageCount: number;
}

function sessionsFile(): string {
  return join(config.agent.sessionDir, "sessions.json");
}

export async function getAllSessions(): Promise<Record<string, SessionData>> {
  try {
    const file = Bun.file(sessionsFile());
    if (await file.exists()) {
      return await file.json();
    }
  } catch {}
  return {};
}

export async function getSession(userId: string): Promise<SessionData | null> {
  const sessions = await getAllSessions();
  return sessions[userId] || null;
}

export async function createSession(userId: string, agentId: string): Promise<SessionData> {
  const sessions = await getAllSessions();
  const session: SessionData = {
    sessionId: crypto.randomUUID(),
    agentId,
    createdAt: new Date().toISOString(),
    lastActive: new Date().toISOString(),
    messageCount: 0,
  };
  sessions[userId] = session;
  await Bun.write(sessionsFile(), JSON.stringify(sessions, null, 2));
  return session;
}

export async function updateSession(userId: string, updates: Partial<SessionData>): Promise<void> {
  const sessions = await getAllSessions();
  if (sessions[userId]) {
    sessions[userId] = { ...sessions[userId], ...updates };
    await Bun.write(sessionsFile(), JSON.stringify(sessions, null, 2));
  }
}

export async function deleteSession(userId: string): Promise<string | null> {
  const sessions = await getAllSessions();
  const old = sessions[userId]?.sessionId || null;
  delete sessions[userId];
  await Bun.write(sessionsFile(), JSON.stringify(sessions, null, 2));
  return old;
}
