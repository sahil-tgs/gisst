/**
 * One-time setup: creates Notion databases on the parent page.
 * Usage: NOTION_API_KEY=ntn_... NOTION_PAGE_ID=abc123... bun scripts/setup-notion.ts
 */

import { setupNotionDatabases } from "../src/notion/schema.ts";

const pageId = process.env.NOTION_PAGE_ID;
const apiKey = process.env.NOTION_API_KEY;

if (!pageId || !apiKey) {
  console.error("Usage: NOTION_API_KEY=ntn_... NOTION_PAGE_ID=abc123... bun scripts/setup-notion.ts");
  process.exit(1);
}

console.log("Setting up Notion databases...");
const ids = await setupNotionDatabases(pageId);
console.log("Done! Database IDs:", ids);
console.log("\nAdd these to your .env:");
console.log(`NOTION_RESEARCH_DB_ID=${ids.researchDb}`);
console.log(`NOTION_DIGEST_DB_ID=${ids.digestDb}`);
