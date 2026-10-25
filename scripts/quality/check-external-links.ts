import { lstat, mkdir, readdir, readFile, writeFile } from "node:fs/promises";
import { basename, dirname, extname, join } from "node:path";

type AvailabilityCheck = {
  availability: "http-response" | "request-error";
  claim_support: "not_assessed";
  error?: string;
  status?: number;
  url: string;
};

type AvailabilityReport = {
  checks: AvailabilityCheck[];
  disclaimer: string;
  generated_at: string;
};

const defaultSourcePaths = [
  "README.md",
  "catalog/curriculum",
  "catalog/resources",
  "docs",
  "labs/freesolv/README.md",
  "report",
  "site/public",
  "site/src/content",
];

const textExtensions = new Set([
  ".astro",
  ".cff",
  ".html",
  ".json",
  ".md",
  ".mdx",
  ".txt",
  ".yaml",
  ".yml",
]);

function compareCodePoints(left: string, right: string): number {
  return left < right ? -1 : left > right ? 1 : 0;
}

function stripTrailingPunctuation(url: string): string {
  return url.replace(/[.,;:!?\])}]+$/u, "");
}

// A literal, unescaped CJK character can never appear in a real URL (it would
// be percent-encoded or punycode), but every bilingual page in this repo
// writes Chinese prose immediately after a markdown link's closing `)` with
// no separating space. The plain-text extraction below has no notion of
// markdown link boundaries, so without this exclusion it swallows the
// following prose into the "URL" up to the next whitespace character,
// producing a garbled string that always fails the availability check.
const cjkAdjacentText = "\\u3000-\\u303f\\u3400-\\u9fff\\uf900-\\ufaff\\uff00-\\uffef";

export function externalUrlsFromText(text: string): string[] {
  const urlPattern = new RegExp(`https?://[^\\s<>'"\`${cjkAdjacentText}]+`, "giu");
  return Array.from(
    new Set(
      Array.from(text.matchAll(urlPattern), (match) =>
        stripTrailingPunctuation(match[0]),
      ).filter((url) => url !== ""),
    ),
  ).sort(compareCodePoints);
}

async function textFiles(path: string): Promise<string[]> {
  const entry = await lstat(path);
  if (entry.isFile()) {
    return textExtensions.has(extname(path).toLowerCase()) ? [path] : [];
  }
  if (!entry.isDirectory()) {
    return [];
  }

  const files: string[] = [];
  for (const name of (await readdir(path)).sort(compareCodePoints)) {
    files.push(...(await textFiles(join(path, name))));
  }
  return files;
}

async function externalUrlsFromPaths(paths: string[]): Promise<string[]> {
  const urls = new Set<string>();
  for (const path of paths) {
    for (const file of await textFiles(path)) {
      for (const url of externalUrlsFromText(await readFile(file, "utf8"))) {
        urls.add(url);
      }
    }
  }
  return Array.from(urls).sort(compareCodePoints);
}

export async function checkExternalUrlAvailability(
  url: string,
): Promise<AvailabilityCheck> {
  try {
    const response = await fetch(url, {
      method: "HEAD",
      redirect: "follow",
      signal: AbortSignal.timeout(15_000),
    });
    return {
      availability: "http-response",
      claim_support: "not_assessed",
      status: response.status,
      url,
    };
  } catch (error: unknown) {
    return {
      availability: "request-error",
      claim_support: "not_assessed",
      error: error instanceof Error ? error.name : "unknown-error",
      url,
    };
  }
}

async function checkAll(urls: string[]): Promise<AvailabilityCheck[]> {
  const results: AvailabilityCheck[] = [];
  let nextIndex = 0;
  const workerCount = Math.min(8, urls.length);

  await Promise.all(
    Array.from({ length: workerCount }, async () => {
      while (nextIndex < urls.length) {
        const index = nextIndex;
        nextIndex += 1;
        results[index] = await checkExternalUrlAvailability(urls[index]);
      }
    }),
  );

  return results;
}

type CliOptions = {
  reportPath: string;
  sourcePaths: string[];
};

function parseArguments(argumentsList: string[]): CliOptions {
  let reportPath = "artifacts/external-links.json";
  const sourcePaths: string[] = [];

  for (let index = 0; index < argumentsList.length; index += 1) {
    const argument = argumentsList[index];
    if (argument === "--report") {
      reportPath = argumentsList[index + 1] ?? "";
      if (reportPath === "") {
        throw new Error("--report requires a path");
      }
      index += 1;
    } else if (argument.startsWith("--")) {
      throw new Error(`Unknown option: ${argument}`);
    } else {
      sourcePaths.push(argument);
    }
  }

  return {
    reportPath,
    sourcePaths: sourcePaths.length > 0 ? sourcePaths : defaultSourcePaths,
  };
}

async function main(): Promise<void> {
  const { reportPath, sourcePaths } = parseArguments(process.argv.slice(2));
  const checks = await checkAll(await externalUrlsFromPaths(sourcePaths));
  const report: AvailabilityReport = {
    checks,
    disclaimer:
      "Availability checks only record request outcomes; they do not establish that a source supports any claim.",
    generated_at: new Date().toISOString(),
  };
  await mkdir(dirname(reportPath), { recursive: true });
  await writeFile(reportPath, `${JSON.stringify(report, null, 2)}\n`);

  console.log(
    `Wrote availability-only report for ${checks.length} external link${checks.length === 1 ? "" : "s"}.`,
  );
}

const invokedAsCli =
  process.argv[1] !== undefined &&
  basename(process.argv[1]) === "check-external-links.ts";

if (invokedAsCli) {
  main().catch((error: unknown) => {
    console.error(error instanceof Error ? error.message : String(error));
    process.exitCode = 1;
  });
}
