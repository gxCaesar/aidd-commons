import { mkdir, writeFile } from "node:fs/promises";
import { resolve } from "node:path";

import { type Resource } from "../../catalog/schema/resource.js";
import {
  CatalogValidationError,
  formatDiagnostic,
  loadCatalog,
} from "./catalog.js";

const csvColumns: Array<keyof Resource> = [
  "id",
  "name",
  "kind",
  "summary",
  "canonical_url",
  "identifiers",
  "stages",
  "modalities",
  "tasks",
  "relations",
  "status",
  "access_level",
  "openness",
  "licenses",
  "evidence",
  "caveats",
  "acknowledgements",
  "last_verified",
];

function parseArguments(argumentsList: string[]): {
  input: string;
  output: string;
  today?: string;
} {
  let input = "catalog/resources";
  let output = "site/public/data";
  let today: string | undefined;

  for (let index = 0; index < argumentsList.length; index += 1) {
    const argument = argumentsList[index];
    if (argument === "--output" || argument === "--today") {
      const value = argumentsList[index + 1];
      if (value === undefined) {
        throw new Error(`${argument} requires a value`);
      }
      if (argument === "--output") {
        output = value;
      } else {
        today = value;
      }
      index += 1;
    } else if (argument.startsWith("--")) {
      throw new Error(`Unknown option: ${argument}`);
    } else {
      input = argument;
    }
  }

  return { input, output, today };
}

function csvValue(value: unknown): string {
  const raw = typeof value === "string" ? value : JSON.stringify(value);
  return /[",\n\r]/.test(raw) ? `"${raw.replaceAll('"', '""')}"` : raw;
}

function resourcesToCsv(resources: Resource[]): string {
  const rows = resources.map((resource) =>
    csvColumns.map((column) => csvValue(resource[column])).join(","),
  );
  return `${csvColumns.join(",")}\n${rows.join("\n")}\n`;
}

async function main(): Promise<void> {
  const { input, output, today } = parseArguments(process.argv.slice(2));
  const resources = await loadCatalog(input, { today });
  const outputDirectory = resolve(output);
  const opennessProjection = resources.map(({ evidence, id, openness }) => {
    const referencedEvidenceIds = new Set(
      Object.values(openness).flatMap((claim) => claim.evidence ?? []),
    );

    return {
      id,
      openness,
      evidence: evidence.filter((item) => referencedEvidenceIds.has(item.id)),
    };
  });

  await mkdir(outputDirectory, { recursive: true });
  await Promise.all([
    writeFile(
      `${outputDirectory}/resources.v1.json`,
      `${JSON.stringify(resources, null, 2)}\n`,
    ),
    writeFile(`${outputDirectory}/resources.v1.csv`, resourcesToCsv(resources)),
    writeFile(
      `${outputDirectory}/openness.v1.json`,
      `${JSON.stringify(opennessProjection, null, 2)}\n`,
    ),
  ]);

  console.log(
    `Exported ${resources.length} resource${resources.length === 1 ? "" : "s"}.`,
  );
}

main().catch((error: unknown) => {
  if (error instanceof CatalogValidationError) {
    for (const diagnostic of error.diagnostics) {
      console.error(formatDiagnostic(diagnostic));
    }
  } else {
    console.error(error instanceof Error ? error.message : String(error));
  }
  process.exitCode = 1;
});
