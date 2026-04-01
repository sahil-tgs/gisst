import { readFileSync, writeFileSync, existsSync } from "fs";

/**
 * Read a JSON file. Works in both Bun and Node.
 */
export async function readJsonFile<T>(path: string): Promise<T | null> {
  try {
    if (typeof Bun !== "undefined") {
      const file = Bun.file(path);
      if (await file.exists()) return await file.json();
    } else {
      if (existsSync(path)) return JSON.parse(readFileSync(path, "utf-8"));
    }
  } catch {}
  return null;
}

/**
 * Write a JSON file. Works in both Bun and Node.
 */
export async function writeJsonFile(path: string, data: unknown): Promise<void> {
  const content = JSON.stringify(data, null, 2);
  if (typeof Bun !== "undefined") {
    await Bun.write(path, content);
  } else {
    writeFileSync(path, content, "utf-8");
  }
}
