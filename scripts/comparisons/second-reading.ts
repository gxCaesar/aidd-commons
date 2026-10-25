import { readdir, readFile } from "node:fs/promises";
import { extname, join, relative, resolve } from "node:path";

import { parse } from "yaml";

import type { ComparisonTaxonomy } from "../../catalog/schema/comparison-taxonomy.js";
import type {
  ComparisonSystem,
  DepthState,
} from "../../catalog/schema/comparison.js";
import {
  ordinalDepth,
  secondReadingSchema,
  type SecondReading,
} from "../../catalog/schema/second-reading.js";
import {
  ComparisonValidationError,
  type ComparisonDiagnostic,
} from "./comparisons.js";
import { boundsAtThreshold, comparisonThresholds } from "./matrix.js";

const rank: Record<Exclude<DepthState, "unverified">, number> = {
  absent: 0,
  mentioned: 1,
  explained: 2,
  worked: 3,
  executable: 4,
  assessed: 5,
};

export async function loadSecondReading(
  inputPath: string,
): Promise<SecondReading> {
  const input = resolve(inputPath);
  const file = relative(process.cwd(), input) || input;
  let source: unknown;
  try {
    source = parse(await readFile(input, "utf8"));
  } catch (error) {
    throw new ComparisonValidationError([
      {
        file,
        field: "$yaml",
        message:
          error instanceof Error ? error.message : "could not parse YAML",
      },
    ]);
  }
  const result = secondReadingSchema.safeParse(source);
  if (!result.success) {
    throw new ComparisonValidationError(
      result.error.issues.map((issue) => ({
        file,
        field: issue.path.map(String).join(".") || "$record",
        message: issue.message,
      })),
    );
  }
  return result.data;
}

export async function loadSecondReadings(
  directory: string,
): Promise<Array<{ file: string; reading: SecondReading }>> {
  const names = (await readdir(resolve(directory)))
    .filter((name) => [".yaml", ".yml"].includes(extname(name)))
    .sort();
  return Promise.all(
    names.map(async (name) => ({
      file: join(directory, name),
      reading: await loadSecondReading(join(directory, name)),
    })),
  );
}

export function assertSecondReadings(
  systems: ComparisonSystem[],
  readings: Array<{ file: string; reading: SecondReading }>,
  taxonomy: ComparisonTaxonomy,
): void {
  const diagnostics = readings.flatMap(({ file, reading }) => {
    const system = systems.find(({ id }) => id === reading.system_id);
    return system === undefined
      ? [
          {
            file,
            field: "system_id",
            message: `names no comparison system: ${reading.system_id}`,
          },
        ]
      : checkAgainstSecondReading(system, reading, taxonomy, file);
  });
  if (diagnostics.length > 0) {
    throw new ComparisonValidationError(diagnostics);
  }
}

// The published row of this project may not claim more than the independent
// reading found. A topic whose material changed after it was read needs a new
// reading, not an override: the gate has no exemption list.
export function checkAgainstSecondReading(
  system: ComparisonSystem,
  reading: SecondReading,
  taxonomy: ComparisonTaxonomy,
  file = "second reading",
): ComparisonDiagnostic[] {
  const diagnostics: ComparisonDiagnostic[] = [];
  if (reading.system_id !== system.id) {
    diagnostics.push({
      file,
      field: "system_id",
      message: `reads ${reading.system_id}, not ${system.id}`,
    });
    return diagnostics;
  }
  const readings = new Map(reading.readings.map((r) => [r.topic_id, r]));
  const observations = new Map(system.coverage.map((c) => [c.topic_id, c]));
  const topicIds = taxonomy.tracks.flatMap((track) =>
    track.topics.map((topic) => topic.id),
  );
  for (const topicId of topicIds) {
    const topicReading = readings.get(topicId);
    if (topicReading === undefined) {
      diagnostics.push({
        file,
        field: topicId,
        message: "has no independent reading",
      });
      continue;
    }
    const observation = observations.get(topicId);
    if (observation === undefined || observation.depth === "unverified") {
      continue;
    }
    const independent = ordinalDepth(topicReading);
    if (rank[observation.depth] > rank[independent]) {
      diagnostics.push({
        file,
        field: topicId,
        message: `records ${observation.depth} but the independent reading supports ${independent}`,
      });
    }
    if (
      observation.run_basis === "real-data" &&
      topicReading.run_basis === "authored" &&
      rank[independent] >= rank.executable
    ) {
      diagnostics.push({
        file,
        field: topicId,
        message:
          "records a real-data run basis but the independent reading found authored inputs",
      });
    }
  }
  for (const topicId of readings.keys()) {
    if (!topicIds.includes(topicId)) {
      diagnostics.push({
        file,
        field: topicId,
        message: "is not a taxonomy topic",
      });
    }
  }
  return diagnostics;
}

export function assertAgainstSecondReading(
  system: ComparisonSystem,
  reading: SecondReading,
  taxonomy: ComparisonTaxonomy,
  file?: string,
): void {
  const diagnostics = checkAgainstSecondReading(
    system,
    reading,
    taxonomy,
    file,
  );
  if (diagnostics.length > 0) {
    throw new ComparisonValidationError(diagnostics);
  }
}

export type SecondReadingSummary = {
  commits: string[];
  cells: number;
  equal: number;
  id: string;
  reading_deeper: number;
  reading_shallower: number;
  reviewed_on: string;
  reviewer: string;
  thresholds: Array<{
    reading: number;
    recorded: number;
    threshold: (typeof comparisonThresholds)[number];
  }>;
};

export function summarizeSecondReading(
  system: ComparisonSystem,
  reading: SecondReading,
): SecondReadingSummary {
  const observations = new Map(system.coverage.map((c) => [c.topic_id, c]));
  let equal = 0;
  let readingDeeper = 0;
  let readingShallower = 0;
  for (const topicReading of reading.readings) {
    const observation = observations.get(topicReading.topic_id);
    if (observation === undefined || observation.depth === "unverified") {
      continue;
    }
    const difference =
      rank[ordinalDepth(topicReading)] - rank[observation.depth];
    if (difference > 0) readingDeeper += 1;
    else if (difference < 0) readingShallower += 1;
    else equal += 1;
  }
  const readingBasis = (basis: string | null) =>
    basis === "real-data" || basis === "authored" ? basis : null;
  return {
    cells: reading.readings.length,
    commits: [
      ...new Set(reading.readings.map((r) => r.reviewed_commit)),
    ].sort(),
    equal,
    id: reading.id,
    reading_deeper: readingDeeper,
    reading_shallower: readingShallower,
    reviewed_on: reading.reviewed_on,
    reviewer: reading.reviewer,
    thresholds: comparisonThresholds.map((threshold) => ({
      reading: reading.readings.reduce(
        (total, r) =>
          total +
          boundsAtThreshold(
            ordinalDepth(r),
            threshold,
            readingBasis(r.run_basis),
          ).lower,
        0,
      ),
      recorded: system.coverage.reduce(
        (total, c) =>
          total +
          boundsAtThreshold(c.depth, threshold, c.run_basis ?? null).lower,
        0,
      ),
      threshold,
    })),
  };
}
