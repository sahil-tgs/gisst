import { join } from "path";
import { config } from "../config.ts";
import { readJsonFile, writeJsonFile } from "../utils/fs.ts";
import type { ScheduleJob } from "../agent/agent-config.ts";

const JOBS_FILE = join(config.agent.configDir, "schedule-jobs.json");

export interface ScheduleJobWithMeta extends ScheduleJob {
  chatId: string;           // Telegram chat ID to send digest to
  createdBy: string;        // User ID who created the job
  lastCrawl?: string;       // ISO timestamp of last crawl
  lastDigest?: string;      // ISO timestamp of last digest sent
}

export async function loadJobs(): Promise<ScheduleJobWithMeta[]> {
  return (await readJsonFile<ScheduleJobWithMeta[]>(JOBS_FILE)) || [];
}

export async function saveJobs(jobs: ScheduleJobWithMeta[]): Promise<void> {
  await writeJsonFile(JOBS_FILE, jobs);
}

export async function addJob(job: ScheduleJobWithMeta): Promise<void> {
  const jobs = await loadJobs();
  jobs.push(job);
  await saveJobs(jobs);
  console.log(`[scheduler] Job added: "${job.topic}" (${job.cadence}, digest at ${job.digestTime})`);
}

export async function removeJob(jobId: string): Promise<ScheduleJobWithMeta | null> {
  const jobs = await loadJobs();
  const idx = jobs.findIndex((j) => j.id === jobId);
  if (idx === -1) return null;
  const [removed] = jobs.splice(idx, 1);
  await saveJobs(jobs);
  return removed;
}

export async function toggleJob(jobId: string): Promise<ScheduleJobWithMeta | null> {
  const jobs = await loadJobs();
  const job = jobs.find((j) => j.id === jobId);
  if (!job) return null;
  job.active = !job.active;
  await saveJobs(jobs);
  return job;
}

export async function updateJobTimestamp(jobId: string, field: "lastCrawl" | "lastDigest"): Promise<void> {
  const jobs = await loadJobs();
  const job = jobs.find((j) => j.id === jobId);
  if (job) {
    job[field] = new Date().toISOString();
    await saveJobs(jobs);
  }
}
