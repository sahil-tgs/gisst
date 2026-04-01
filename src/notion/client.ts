import { Client } from "@notionhq/client";
import { config } from "../config.ts";

let notion: Client | null = null;

export function getNotion(): Client {
  if (!notion) {
    if (!config.notion.apiKey) {
      throw new Error("NOTION_API_KEY not set");
    }
    notion = new Client({ auth: config.notion.apiKey });
  }
  return notion;
}

/**
 * Create a database under a parent page.
 */
export async function createDatabase(
  parentPageId: string,
  title: string,
  properties: Record<string, any>
): Promise<string> {
  const n = getNotion();
  const db = await n.databases.create({
    parent: { type: "page_id", page_id: parentPageId },
    title: [{ type: "text", text: { content: title } }],
    properties,
  });
  return db.id;
}

/**
 * Create a page in a database.
 */
export async function createPage(
  databaseId: string,
  properties: Record<string, any>,
  children?: any[]
): Promise<string> {
  const n = getNotion();
  const page = await n.pages.create({
    parent: { type: "database_id", database_id: databaseId },
    properties,
    children: children || [],
  });
  return page.id;
}

/**
 * Query a database with optional filter.
 */
export async function queryDatabase(
  databaseId: string,
  filter?: any,
  sorts?: any[]
): Promise<any[]> {
  const n = getNotion();
  const response = await n.databases.query({
    database_id: databaseId,
    filter,
    sorts,
  });
  return response.results;
}
