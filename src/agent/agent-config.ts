import { join } from "path";
import { config } from "../config.ts";

export interface AgentIdentity {
  name: string;
  tone: "professional" | "casual" | "academic" | "journalist";
  language: string;
  emojiStyle: boolean;
}

export interface ResearchSettings {
  depth: "quick" | "standard" | "deep";
  topics: string[];
  sourcePreferences: ("news" | "academic" | "social" | "all")[];
  platformPriority: string[];
  autoCite: "inline" | "footnote";
}

export interface InteractionSettings {
  responseLength: "concise" | "standard" | "detailed";
  followUp: boolean;
  autoSave: boolean;
  triggerMode: "all" | "mention" | "command";
}

export interface ScheduleJob {
  id: string;
  topic: string;
  keywords: string[];
  cadence: string;
  digestTime: string;
  digestTimezone: string;
  lookbackWindow: string;
  platformPriority: string[];
  active: boolean;
}

export interface ScheduleSettings {
  jobs: ScheduleJob[];
  maxJobsPerDay: number;
  quietHours: { start: string; end: string };
  defaultDigestTime: string;
  defaultTimezone: string;
}

export interface AgentConfig {
  id: string;
  createdAt: string;
  updatedAt: string;
  identity: AgentIdentity;
  research: ResearchSettings;
  interaction: InteractionSettings;
  schedule: ScheduleSettings;
}

const DEFAULTS: Omit<AgentConfig, "id" | "createdAt" | "updatedAt"> = {
  identity: {
    name: "Scout",
    tone: "professional",
    language: "en",
    emojiStyle: true,
  },
  research: {
    depth: "standard",
    topics: [],
    sourcePreferences: ["all"],
    platformPriority: [],
    autoCite: "footnote",
  },
  interaction: {
    responseLength: "standard",
    followUp: true,
    autoSave: true,
    triggerMode: "command",
  },
  schedule: {
    jobs: [],
    maxJobsPerDay: 20,
    quietHours: { start: "23:00", end: "06:00" },
    defaultDigestTime: "20:00",
    defaultTimezone: "UTC",
  },
};

function agentConfigFile(agentId: string): string {
  return join(config.agent.configDir, `${agentId}.json`);
}

export async function loadAgentConfig(agentId: string): Promise<AgentConfig | null> {
  try {
    const file = Bun.file(agentConfigFile(agentId));
    if (await file.exists()) {
      return await file.json();
    }
  } catch {}
  return null;
}

export async function createAgentConfig(overrides?: Partial<AgentConfig>): Promise<AgentConfig> {
  const now = new Date().toISOString();
  const agentConfig: AgentConfig = {
    id: crypto.randomUUID(),
    createdAt: now,
    updatedAt: now,
    ...DEFAULTS,
    ...overrides,
    identity: { ...DEFAULTS.identity, ...overrides?.identity },
    research: { ...DEFAULTS.research, ...overrides?.research },
    interaction: { ...DEFAULTS.interaction, ...overrides?.interaction },
    schedule: { ...DEFAULTS.schedule, ...overrides?.schedule },
  };
  await Bun.write(agentConfigFile(agentConfig.id), JSON.stringify(agentConfig, null, 2));
  return agentConfig;
}

export async function updateAgentConfig(
  agentId: string,
  updates: Partial<AgentConfig>
): Promise<AgentConfig | null> {
  const existing = await loadAgentConfig(agentId);
  if (!existing) return null;

  const updated: AgentConfig = {
    ...existing,
    ...updates,
    updatedAt: new Date().toISOString(),
    identity: { ...existing.identity, ...updates.identity },
    research: { ...existing.research, ...updates.research },
    interaction: { ...existing.interaction, ...updates.interaction },
    schedule: { ...existing.schedule, ...updates.schedule },
  };
  await Bun.write(agentConfigFile(agentId), JSON.stringify(updated, null, 2));
  return updated;
}

export function getDefaults() {
  return structuredClone(DEFAULTS);
}
