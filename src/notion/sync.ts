import { createPage } from "./client.ts";
import { getNotionDatabaseIds } from "./schema.ts";
import type { NotionSyncPayload } from "../agent/claude.ts";

/**
 * Save a research finding to Notion.
 * Called when agent output contains [SAVE_TO_NOTION: {...}].
 */
export async function syncResearchToNotion(
  payload: NotionSyncPayload,
  meta: { userName?: string; sessionId?: string; type?: string }
): Promise<string | null> {
  const ids = await getNotionDatabaseIds();
  if (!ids) {
    console.log("[notion] Not set up — skipping sync");
    return null;
  }

  try {
    const sourcesText = payload.sources
      ?.map((s, i) => `[${i + 1}] ${s.title}: ${s.url}`)
      .join("\n") || "";

    const pageId = await createPage(ids.researchDb, {
      Title: { title: [{ text: { content: payload.title } }] },
      Topic: payload.topic ? { select: { name: payload.topic } } : undefined,
      Summary: { rich_text: [{ text: { content: (payload.summary || "").slice(0, 2000) } }] },
      Sources: { rich_text: [{ text: { content: sourcesText.slice(0, 2000) } }] },
      Tags: payload.tags ? { multi_select: payload.tags.slice(0, 10).map((t) => ({ name: t })) } : undefined,
      Date: { date: { start: new Date().toISOString().split("T")[0] } },
      Researcher: meta.userName ? { rich_text: [{ text: { content: meta.userName } }] } : undefined,
      "Session ID": meta.sessionId ? { rich_text: [{ text: { content: meta.sessionId } }] } : undefined,
      Type: { select: { name: meta.type || "Research" } },
    }, [
      // Add key findings as bullet list in the page body
      ...(payload.keyFindings || []).map((finding) => ({
        object: "block" as const,
        type: "bulleted_list_item" as const,
        bulleted_list_item: {
          rich_text: [{ type: "text" as const, text: { content: finding.slice(0, 2000) } }],
        },
      })),
    ]);

    console.log(`[notion] Saved research: "${payload.title}" (${pageId.slice(0, 8)})`);
    return pageId;
  } catch (err) {
    console.error("[notion] Failed to sync research:", err);
    return null;
  }
}

/**
 * Save a digest to Notion.
 */
export async function syncDigestToNotion(
  topic: string,
  summary: string,
  findingCount: number,
  scheduleId: string
): Promise<string | null> {
  const ids = await getNotionDatabaseIds();
  if (!ids) return null;

  try {
    const pageId = await createPage(ids.digestDb, {
      Title: { title: [{ text: { content: `${topic} — ${new Date().toISOString().split("T")[0]}` } }] },
      Topic: { rich_text: [{ text: { content: topic } }] },
      Date: { date: { start: new Date().toISOString().split("T")[0] } },
      "Finding Count": { number: findingCount },
      "Schedule ID": { rich_text: [{ text: { content: scheduleId } }] },
      Summary: { rich_text: [{ text: { content: summary.slice(0, 2000) } }] },
    }, [
      {
        object: "block" as const,
        type: "paragraph" as const,
        paragraph: {
          rich_text: [{ type: "text" as const, text: { content: summary.slice(0, 2000) } }],
        },
      },
    ]);

    console.log(`[notion] Saved digest: "${topic}" (${pageId.slice(0, 8)})`);
    return pageId;
  } catch (err) {
    console.error("[notion] Failed to sync digest:", err);
    return null;
  }
}

/**
 * Save a crawl finding to Notion (individual crawl result from scheduler).
 */
export async function syncCrawlToNotion(
  topic: string,
  content: string,
  scheduleId: string
): Promise<string | null> {
  const ids = await getNotionDatabaseIds();
  if (!ids) return null;

  try {
    const pageId = await createPage(ids.researchDb, {
      Title: { title: [{ text: { content: `${topic} — Crawl ${new Date().toISOString().split("T")[0]}` } }] },
      Topic: { select: { name: topic } },
      Summary: { rich_text: [{ text: { content: content.slice(0, 2000) } }] },
      Date: { date: { start: new Date().toISOString().split("T")[0] } },
      "Session ID": { rich_text: [{ text: { content: scheduleId } }] },
      Type: { select: { name: "Crawl" } },
    });

    console.log(`[notion] Saved crawl: "${topic}" (${pageId.slice(0, 8)})`);
    return pageId;
  } catch (err) {
    console.error("[notion] Failed to sync crawl:", err);
    return null;
  }
}
