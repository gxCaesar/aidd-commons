import { readFile } from "node:fs/promises";
import { basename } from "node:path";

function compareCodePoints(left: string, right: string): number {
  return left < right ? -1 : left > right ? 1 : 0;
}

function citationKeys(markdown: string): Set<string> {
  return new Set(
    Array.from(
      markdown.matchAll(/@([A-Za-z0-9_:.+-]+)/gu),
      (match) => match[1],
    ),
  );
}

function bibliographyKeys(bibtex: string): Set<string> {
  return new Set(
    Array.from(
      bibtex.matchAll(/@[A-Za-z]+\s*\{\s*([^,\s]+)/gu),
      (match) => match[1],
    ),
  );
}

export async function findUnresolvedCitationKeys(
  reportPath: string,
  bibliographyPath: string,
): Promise<string[]> {
  const [report, bibliography] = await Promise.all([
    readFile(reportPath, "utf8"),
    readFile(bibliographyPath, "utf8"),
  ]);
  const knownKeys = bibliographyKeys(bibliography);

  return Array.from(citationKeys(report))
    .filter((key) => !knownKeys.has(key))
    .sort(compareCodePoints);
}

async function main(): Promise<void> {
  const [
    reportPath = "report/aidd-commons-living-report-v0.1.md",
    bibliographyPath = "report/references.bib",
  ] = process.argv.slice(2);
  const unresolved = await findUnresolvedCitationKeys(
    reportPath,
    bibliographyPath,
  );

  if (unresolved.length > 0) {
    console.error(`Unresolved citation keys: ${unresolved.join(", ")}`);
    process.exitCode = 1;
    return;
  }

  console.log("Citation keys resolve.");
}

const invokedAsCli =
  process.argv[1] !== undefined &&
  basename(process.argv[1]) === "check-citations.ts";

if (invokedAsCli) {
  main().catch((error: unknown) => {
    console.error(error instanceof Error ? error.message : String(error));
    process.exitCode = 1;
  });
}
