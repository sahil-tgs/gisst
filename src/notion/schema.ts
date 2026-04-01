import { createDatabase } from "./client.ts";
import { config } from "../config.ts";
import { readJsonFile, writeJsonFile } from "../utils/fs.ts";
import { join } from "path";

const NOTION_IDS_FILE = join(config.agent.configDir, "notion-databases.json");

export interface NotionDatabaseIds {
  researchDb: string;
  digestDb: string;
}

export async function getNotionDatabaseIds(): Promise<NotionDatabaseIds | null> {
  return readJsonFile<NotionDatabaseIds>(NOTION_IDS_FILE);
}

async function saveNotionDatabaseIds(ids: NotionDatabaseIds): Promise<void> {
  await writeJsonFile(NOTION_IDS_FILE, ids);
}

/**
 * Create the Research Findings and Daily Digests databases on the parent page.
 * Only runs once — saves database IDs for future use.
 */
export async function setupNotionDatabases(parentPageId: string): Promise<NotionDatabaseIds> {
  // Check if already set up
  const existing = await getNotionDatabaseIds();
  if (existing) {
    console.log("[notion] Databases already set up");
    return existing;
  }

  console.log("[notion] Creating Research Findings database...");
  const researchDb = await createDatabase(parentPageId, "Research Findings", {
    Title: { title: {} },
    Topic: { select: { options: [] } },
    Summary: { rich_text: {} },
    Sources: { rich_text: {} },
    Tags: { multi_select: { options: [] } },
    Date: { date: {} },
    "Researcher": { rich_text: {} },
    "Session ID": { rich_text: {} },
    Type: {
      select: {
        options: [
          { name: "Research", color: "blue" },
          { name: "Crawl", color: "green" },
          { name: "Digest", color: "purple" },
        ],
      },
    },
  });

  console.log("[notion] Creating Daily Digests database...");
  const digestDb = await createDatabase(parentPageId, "Daily Digests", {
    Title: { title: {} },
    Topic: { rich_text: {} },
    Date: { date: {} },
    "Finding Count": { number: {} },
    "Schedule ID": { rich_text: {} },
    Summary: { rich_text: {} },
  });

  const ids = { researchDb, digestDb };
  await saveNotionDatabaseIds(ids);
  console.log(`[notion] Databases created: research=${researchDb.slice(0, 8)}, digest=${digestDb.slice(0, 8)}`);
  return ids;
}
