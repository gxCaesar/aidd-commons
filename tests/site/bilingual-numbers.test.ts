import { readFile, readdir } from "node:fs/promises";
import { join, relative } from "node:path";
import { fileURLToPath } from "node:url";

import { describe, expect, it } from "vitest";

const repositoryRoot = fileURLToPath(new URL("../..", import.meta.url));
const englishRoot = join(repositoryRoot, "site/src/content/docs");
const chineseRoot = join(englishRoot, "zh-cn");

// Decimals and three-digit-or-longer integers: measured values, counts, versions
// and identifiers. Shorter integers are skipped because dates, list positions and
// ordinary prose numbers legitimately read differently in the two editions.
const significantNumber = /\d+\.\d+|\d{3,}/g;

// The Chinese edition may write a probability where the English writes a percent.
// Everything else must appear in both editions, in the same written form.
function unmatched(numbers: Set<string>, other: Set<string>, otherText: string): string[] {
  return [...numbers].filter((value) => {
    if (other.has(value)) return false;
    const parsed = Number(value);
    if (!(parsed > 0 && parsed < 1)) return true;
    const percent = Math.round(parsed * 10000) / 100;
    return !otherText.includes(`${percent}%`);
  });
}

async function pageFiles(root: string): Promise<string[]> {
  const entries = await readdir(root, { withFileTypes: true, recursive: true });
  return entries
    .filter((entry) => entry.isFile() && entry.name.endsWith(".mdx"))
    .map((entry) => relative(root, join(entry.parentPath, entry.name)))
    .sort();
}

describe("bilingual teaching pages", () => {
  it("state the same significant numbers in both editions", async () => {
    const translated = (await pageFiles(chineseRoot)).filter(
      (file) => !file.startsWith("pathways/"),
    );
    expect(translated.length).toBeGreaterThan(50);
    const drift: string[] = [];
    for (const file of translated) {
      const chinese = await readFile(join(chineseRoot, file), "utf8");
      const english = await readFile(join(englishRoot, file), "utf8").catch(() => null);
      if (english === null) {
        drift.push(`${file}: no English counterpart`);
        continue;
      }
      const inChinese = new Set(chinese.match(significantNumber) ?? []);
      const inEnglish = new Set(english.match(significantNumber) ?? []);
      const missingFromChinese = unmatched(inEnglish, inChinese, chinese);
      const missingFromEnglish = unmatched(inChinese, inEnglish, english);
      if (missingFromChinese.length > 0) {
        drift.push(`${file}: absent from the Chinese page: ${missingFromChinese.join(", ")}`);
      }
      if (missingFromEnglish.length > 0) {
        drift.push(`${file}: absent from the English page: ${missingFromEnglish.join(", ")}`);
      }
    }
    expect(drift).toEqual([]);
  });

  it("reports a rounded or dropped number instead of accepting it", () => {
    const english = "Morgan Ridge primary MAE is 0.41833032711934154 across 132 parents.";
    const chinese = "Morgan Ridge 主要 MAE 为 0.418，覆盖 132 个 parent。";
    const inEnglish = new Set(english.match(significantNumber) ?? []);
    const inChinese = new Set(chinese.match(significantNumber) ?? []);
    expect(unmatched(inEnglish, inChinese, chinese)).toEqual(["0.41833032711934154"]);
    expect(unmatched(inChinese, inEnglish, english)).toEqual(["0.418"]);
  });

  it("accepts a probability written as a percent in the other edition", () => {
    const english = "so the 90% set is {u1, u2, u3}.";
    const chinese = "`u1 + u2 = 0.82`，低于 0.90；最小 90% 可信集是 {u1, u2, u3}。";
    const inEnglish = new Set(english.match(significantNumber) ?? []);
    const inChinese = new Set(chinese.match(significantNumber) ?? []);
    expect(unmatched(inChinese, inEnglish, english)).toEqual(["0.82"]);
    expect(unmatched(new Set(["0.90"]), inEnglish, english)).toEqual([]);
  });
});
