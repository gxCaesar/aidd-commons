import { readFile, readdir } from "node:fs/promises";
import { existsSync } from "node:fs";
import { join, relative } from "node:path";
import { fileURLToPath } from "node:url";

import { describe, expect, it } from "vitest";

const repositoryRoot = fileURLToPath(new URL("../..", import.meta.url));
const contentRoot = join(repositoryRoot, "site/src/content/docs");

// The shared notebook practice guide is counted separately in the prose, so it
// never belongs to the lab-guide total.
const notebookGuide = "notebook-guide.mdx";

async function mdxFiles(root: string): Promise<string[]> {
  const entries = await readdir(root, { withFileTypes: true, recursive: true });
  return entries
    .filter((entry) => entry.isFile() && entry.name.endsWith(".mdx"))
    .map((entry) => relative(root, join(entry.parentPath, entry.name)))
    .sort();
}

function countPages(
  files: string[],
  options: { excludedSegments?: string[]; excludedNames?: string[] } = {},
): number {
  const excludedSegments = new Set(options.excludedSegments ?? []);
  const excludedNames = new Set(options.excludedNames ?? []);
  return files.filter((file) => {
    const segments = file.split(/[\\/]/);
    if (segments.some((segment) => excludedSegments.has(segment))) return false;
    return !excludedNames.has(file);
  }).length;
}

type Counts = {
  chineseLabGuides: number;
  chineseLearnPages: number;
  englishLabGuides: number;
  englishLearnPages: number;
};

async function measurePages(): Promise<Counts> {
  const englishLearn = await mdxFiles(join(contentRoot, "learn"));
  const chineseLearn = await mdxFiles(join(contentRoot, "zh-cn", "learn"));
  const englishLabs = await mdxFiles(join(contentRoot, "labs"));
  const chineseLabs = await mdxFiles(join(contentRoot, "zh-cn", "labs"));
  return {
    englishLearnPages: countPages(englishLearn, {
      excludedSegments: ["zh-cn"],
    }),
    chineseLearnPages: countPages(chineseLearn),
    englishLabGuides: countPages(englishLabs, {
      excludedSegments: ["zh-cn"],
      excludedNames: [notebookGuide],
    }),
    chineseLabGuides: countPages(chineseLabs, {
      excludedNames: [notebookGuide],
    }),
  };
}

// The body of one "## " section, up to the next section of the same level. The
// heading is matched by prefix because round summaries carry a date.
function sectionBody(text: string, heading: string): string | null {
  const chunk = text
    .split(/^## /m)
    .find((part) => part.split("\n", 1)[0]?.startsWith(heading) === true);
  return chunk ?? null;
}

// Every prose claim below names one sentence, not a page of digits. The files
// carry versions, dates, protocol constants and track counts that are not
// derived from the filesystem, so a blanket digit scan would be both wrong and
// unusable.
type Claim = {
  file: string;
  label: string;
  // The measurement the sentence is expected to agree with.
  subject: keyof Counts;
  pattern: RegExp;
  // A heading whose body holds the claim, when a document also preserves
  // historical counts outside its current public delivery section.
  section?: string;
};

const learnClaims: Claim[] = [
  {
    file: "README.md",
    label: "current Learn pages",
    subject: "chineseLearnPages",
    pattern: /translations of the current (\d+) Learn pages/,
  },
  {
    file: "docs/CHINESE_EDITION.md",
    label: "translated Learn pages",
    subject: "chineseLearnPages",
    pattern: /translations of all (\d+) current Learn\s+pages/,
  },
  {
    file: "docs/CHINESE_EDITION.md",
    label: "current page count",
    subject: "chineseLearnPages",
    pattern: /brings the current count to (\d+)/,
  },
  {
    file: "docs/PUBLIC_ROADMAP.md",
    label: "English learn pages",
    subject: "englishLearnPages",
    pattern: /English Learn pages: (\d+)/,
  },
];

const labClaims: Claim[] = [
  {
    file: "README.md",
    label: "lab guides",
    subject: "chineseLabGuides",
    pattern: /(\d+) lab guides and a shared notebook practice guide/,
  },
  {
    file: "docs/CHINESE_EDITION.md",
    label: "lab guides",
    subject: "chineseLabGuides",
    pattern: /all (\d+) lab guides and a shared notebook practice guide/,
  },
  {
    file: "docs/CHINESE_EDITION.md",
    label: "translated lab guides",
    subject: "chineseLabGuides",
    pattern: /links the (\d+) translated lab guides/,
  },
  {
    file: "site/src/pages/zh-cn/index.astro",
    label: "lab guides",
    subject: "chineseLabGuides",
    pattern: /现有课程正文和 (\d+) 个实验说明的译文/,
  },
];

async function collectDrift(
  claims: Claim[],
  counts: Counts,
): Promise<string[]> {
  const drift: string[] = [];
  for (const claim of claims) {
    const file = await readFile(join(repositoryRoot, claim.file), "utf8");
    let text = file;
    if (claim.section !== undefined) {
      const body = sectionBody(file, claim.section);
      if (body === null) {
        drift.push(`${claim.file}: no "${claim.section}" section was found`);
        continue;
      }
      text = body;
    }
    const matches = [...text.matchAll(new RegExp(claim.pattern.source, "g"))];
    if (matches.length === 0) {
      drift.push(
        `${claim.file}: no sentence matching ${claim.pattern.source} was found`,
      );
      continue;
    }
    if (matches.length > 1) {
      drift.push(
        `${claim.file}: ${matches.length} sentences match ${claim.pattern.source}; the claim is ambiguous`,
      );
      continue;
    }
    const stated = Number(matches[0]?.[1]);
    if (!Number.isInteger(stated)) {
      drift.push(`${claim.file}: ${claim.label} is not a count ("${stated}")`);
      continue;
    }
    const measured = counts[claim.subject];
    if (stated !== measured) {
      drift.push(
        `${claim.file}: ${claim.label} says ${stated}, the filesystem has ${measured}`,
      );
    }
  }
  return drift;
}

// The prose number is what pytest reports, which counts collected cases. A
// parametrized case expands one "def test_" function into several, so the
// collected count is never below the number of test functions on disk.
async function countTestFunctions(): Promise<number> {
  const root = join(repositoryRoot, "labs", "tests");
  const entries = await readdir(root, { withFileTypes: true, recursive: true });
  let functions = 0;
  for (const entry of entries) {
    if (!entry.isFile() || !entry.name.endsWith(".py")) continue;
    const text = await readFile(join(entry.parentPath, entry.name), "utf8");
    functions += (text.match(/^[ \t]*def test_/gm) ?? []).length;
  }
  return functions;
}

const pytestClaims = [
  { file: "CLAUDE.md", label: "pytest command comment" },
  { file: "AGENTS.md", label: "pytest command comment" },
];

async function collectPytestDrift(): Promise<string[]> {
  const drift: string[] = [];
  const functions = await countTestFunctions();
  for (const claim of pytestClaims) {
    const text = await readFile(join(repositoryRoot, claim.file), "utf8");
    const match = /-m pytest labs\/tests\s+#\s*(\d+)\s+tests/.exec(text);
    if (match === null) {
      drift.push(`${claim.file}: no pytest command comment carrying a count`);
      continue;
    }
    const stated = Number(match[1]);
    if (stated < functions) {
      drift.push(
        `${claim.file}: ${claim.label} says ${stated}, the disk holds ${functions} test functions`,
      );
    }
  }
  return drift;
}

describe("hand-maintained counts in reader-facing prose", () => {
  it("measures the pages and test functions it claims to count", async () => {
    const counts = await measurePages();
    expect(counts.englishLearnPages).toBeGreaterThan(50);
    expect(counts.englishLabGuides).toBeGreaterThan(10);
    expect(await countTestFunctions()).toBeGreaterThan(100);
  });

  it("states the number of Learn pages that exist", async () => {
    const counts = await measurePages();
    expect(await collectDrift(learnClaims, counts)).toEqual([]);
  });

  it("states the number of lab guides that exist", async () => {
    const counts = await measurePages();
    expect(await collectDrift(labClaims, counts)).toEqual([]);
  });

  // Both local agent guides are intentionally absent from the public source.
  // If either guide exists, still check both so a partial omission is visible.
  it.skipIf(
    !pytestClaims.some((claim) => existsSync(join(repositoryRoot, claim.file))),
  )(
    "states a pytest count in local agent guides that covers every test function on disk",
    async () => {
      expect(await collectPytestDrift()).toEqual([]);
    },
  );

  it("mirrors every Learn page and lab guide in the Chinese edition", async () => {
    const counts = await measurePages();
    expect(counts.chineseLearnPages).toBe(counts.englishLearnPages);
    expect(counts.chineseLabGuides).toBe(counts.englishLabGuides);
  });
});
