import { join } from "path";
import { mkdirSync } from "fs";
import { config } from "../config.ts";
import { readJsonFile, writeJsonFile } from "../utils/fs.ts";

export interface StagedFinding {
  crawlTime: string;
  content: string;
}

function stagingFile(jobId: string, date: string): string {
  const dir = join(config.agent.stagingDir, jobId);
  mkdirSync(dir, { recursive: true });
  return join(dir, `${date}.json`);
}

function today(): string {
  return new Date().toISOString().split("T")[0];
}

/**
 * Append a crawl result to the staging area for a job.
 */
export async function stageFinding(jobId: string, content: string): Promise<void> {
  const file = stagingFile(jobId, today());
  const existing = (await readJsonFile<StagedFinding[]>(file)) || [];
  existing.push({
    crawlTime: new Date().toISOString(),
    content,
  });
  await writeJsonFile(file, existing);
  console.log(`[staging] Saved finding for job ${jobId} (${existing.length} total today)`);
}

/**
 * Load all staged findings for a job today.
 */
export async function loadStagedFindings(jobId: string): Promise<StagedFinding[]> {
  const file = stagingFile(jobId, today());
  return (await readJsonFile<StagedFinding[]>(file)) || [];
}

/**
 * Clear staged findings for a job after digest is sent.
 */
export async function clearStaging(jobId: string): Promise<void> {
  const file = stagingFile(jobId, today());
  await writeJsonFile(file, []);
}
