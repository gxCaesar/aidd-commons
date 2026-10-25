import { readdir, readFile } from "node:fs/promises";
import { join } from "node:path";
import { fileURLToPath } from "node:url";

import { describe, expect, it } from "vitest";

const repositoryRoot = fileURLToPath(new URL("../..", import.meta.url));
const contentRoot = join(repositoryRoot, "site/src/content/docs");

// The shared notebook practice guide is counted and linked separately, so it
// never belongs to the laboratory-guide index.
const notebookGuide = "notebook-guide.mdx";

async function guideSlugs(directory: string): Promise<string[]> {
  const entries = await readdir(directory, { withFileTypes: true });
  return entries
    .filter((entry) => entry.isFile() && entry.name.endsWith(".mdx"))
    .map((entry) => entry.name)
    .filter((name) => name !== notebookGuide)
    .map((name) => name.replace(/\.mdx$/u, ""))
    .sort();
}

// The English index is hand-written markup and the Chinese one is a data
// array, so the two are read differently but must cover the same guides.
async function englishIndexSlugs(): Promise<string[]> {
  const document = await readFile(
    join(repositoryRoot, "site/src/pages/labs/index.astro"),
    "utf8",
  );
  return Array.from(
    document.matchAll(/href="\/labs\/([^/"]+)\/"/gu),
    (match) => match[1]!,
  ).sort();
}

async function chineseIndexSlugs(): Promise<string[]> {
  const document = await readFile(
    join(repositoryRoot, "site/src/pages/zh-cn/labs/index.astro"),
    "utf8",
  );
  return Array.from(
    document.matchAll(/slug:\s*"([^"]+)"/gu),
    (match) => match[1]!,
  ).sort();
}

describe("the laboratories index lists every laboratory guide", () => {
  it("links every English guide from the English index", async () => {
    const guides = await guideSlugs(join(contentRoot, "labs"));
    const linked = await englishIndexSlugs();
    expect(
      linked.filter((slug) => !guides.includes(slug) && slug !== "notebook-guide"),
    ).toEqual([]);
    expect(guides.filter((slug) => !linked.includes(slug))).toEqual([]);
  });

  it("links every Chinese guide from the Chinese index", async () => {
    const guides = await guideSlugs(join(contentRoot, "zh-cn", "labs"));
    const linked = await chineseIndexSlugs();
    expect(
      linked.filter((slug) => !guides.includes(slug) && slug !== "notebook-guide"),
    ).toEqual([]);
    expect(guides.filter((slug) => !linked.includes(slug))).toEqual([]);
  });

  it("carries the same set of guides in the two editions", async () => {
    const english = await guideSlugs(join(contentRoot, "labs"));
    const chinese = await guideSlugs(join(contentRoot, "zh-cn", "labs"));
    expect(chinese).toEqual(english);
  });
});
