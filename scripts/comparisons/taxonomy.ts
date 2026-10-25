import { readFile } from "node:fs/promises";
import { relative, resolve } from "node:path";

import { parse } from "yaml";

import {
  comparisonTaxonomySchema,
  type ComparisonTaxonomy,
} from "../../catalog/schema/comparison-taxonomy.js";
import type { ComparisonSystem } from "../../catalog/schema/comparison.js";
import { expectedTrackIds } from "../curriculum/curriculum.js";

export type ComparisonTaxonomyDiagnostic = {
  file: string;
  field: string;
  message: string;
};

export class ComparisonTaxonomyValidationError extends Error {
  constructor(readonly diagnostics: ComparisonTaxonomyDiagnostic[]) {
    super(diagnostics.map(formatComparisonTaxonomyDiagnostic).join("\n"));
    this.name = "ComparisonTaxonomyValidationError";
  }
}

export function formatComparisonTaxonomyDiagnostic(
  diagnostic: ComparisonTaxonomyDiagnostic,
): string {
  return `${diagnostic.file}: ${diagnostic.field}: ${diagnostic.message}`;
}

export async function loadComparisonTaxonomy(
  inputPath: string,
): Promise<ComparisonTaxonomy> {
  const input = resolve(inputPath);
  const file = relative(process.cwd(), input) || input;
  let source: unknown;

  try {
    source = parse(await readFile(input, "utf8"), { merge: true });
  } catch (error) {
    throw new ComparisonTaxonomyValidationError([
      {
        file,
        field: "$yaml",
        message:
          error instanceof Error ? error.message : "could not parse YAML",
      },
    ]);
  }

  const result = comparisonTaxonomySchema.safeParse(source);
  if (!result.success) {
    throw new ComparisonTaxonomyValidationError(
      result.error.issues.map((issue) => ({
        file,
        field: issue.path.map(String).join(".") || "$taxonomy",
        message: issue.message,
      })),
    );
  }

  const taxonomy = result.data;
  const diagnostics: ComparisonTaxonomyDiagnostic[] = [];
  const trackIndexes = new Map<string, number>();
  const topicIndexes = new Map<
    string,
    { trackIndex: number; topicIndex: number; globalIndex: number }
  >();
  let globalIndex = 0;

  if (taxonomy.tracks.length !== expectedTrackIds.length) {
    diagnostics.push({
      file,
      field: "tracks",
      message: `must define exactly ${expectedTrackIds.length} tracks`,
    });
  }

  for (const [trackIndex, track] of taxonomy.tracks.entries()) {
    const expectedId = expectedTrackIds[trackIndex];
    if (track.id !== expectedId) {
      diagnostics.push({
        file,
        field: `tracks.${trackIndex}.id`,
        message: `must be ${expectedId ?? "an expected charter track ID"}`,
      });
    }
    if (track.order !== trackIndex + 1) {
      diagnostics.push({
        file,
        field: `tracks.${trackIndex}.order`,
        message: "must be sequential starting at 1",
      });
    }
    const firstTrackIndex = trackIndexes.get(track.id);
    if (firstTrackIndex !== undefined) {
      diagnostics.push({
        file,
        field: `tracks.${trackIndex}.id`,
        message: `duplicates track ID declared at tracks.${firstTrackIndex}`,
      });
    } else {
      trackIndexes.set(track.id, trackIndex);
    }

    if (!track.topics.some(({ core }) => core)) {
      diagnostics.push({
        file,
        field: `tracks.${trackIndex}.topics`,
        message: "must contain at least one core topic",
      });
    }

    for (const [topicIndex, topic] of track.topics.entries()) {
      if (topic.order !== topicIndex + 1) {
        diagnostics.push({
          file,
          field: `tracks.${trackIndex}.topics.${topicIndex}.order`,
          message: "must be sequential within its track starting at 1",
        });
      }

      const firstTopic = topicIndexes.get(topic.id);
      if (firstTopic !== undefined) {
        diagnostics.push({
          file,
          field: `tracks.${trackIndex}.topics.${topicIndex}.id`,
          message: `duplicates topic ID declared at tracks.${firstTopic.trackIndex}.topics.${firstTopic.topicIndex}`,
        });
      } else {
        topicIndexes.set(topic.id, { trackIndex, topicIndex, globalIndex });
      }
      globalIndex += 1;
    }
  }

  globalIndex = 0;
  for (const [trackIndex, track] of taxonomy.tracks.entries()) {
    for (const [topicIndex, topic] of track.topics.entries()) {
      for (const [
        prerequisiteIndex,
        prerequisite,
      ] of topic.prerequisites.entries()) {
        const referencedTopic = topicIndexes.get(prerequisite);
        const field = `tracks.${trackIndex}.topics.${topicIndex}.prerequisites.${prerequisiteIndex}`;
        if (referencedTopic === undefined) {
          diagnostics.push({
            file,
            field,
            message: `does not resolve to a taxonomy topic ID: ${prerequisite}`,
          });
        } else if (referencedTopic.globalIndex >= globalIndex) {
          diagnostics.push({
            file,
            field,
            message: "must point to an earlier topic in taxonomy order",
          });
        }
      }
      globalIndex += 1;
    }
  }

  if (diagnostics.length > 0) {
    throw new ComparisonTaxonomyValidationError(diagnostics);
  }
  return taxonomy;
}

export function validateCoverageTopics(
  systems: ComparisonSystem[],
  taxonomy: ComparisonTaxonomy,
): void {
  const orderedTopicIds = taxonomy.tracks.flatMap((track) =>
    track.topics.map((topic) => topic.id),
  );
  const topicIds = new Set(orderedTopicIds);
  const diagnostics: ComparisonTaxonomyDiagnostic[] = [];

  for (const system of systems) {
    for (const [index, observation] of system.coverage.entries()) {
      if (!topicIds.has(observation.topic_id)) {
        diagnostics.push({
          file: `comparison-system:${system.id}`,
          field: `coverage.${index}.topic_id`,
          message: `does not resolve to a taxonomy topic: ${observation.topic_id}`,
        });
      }
    }

    const observedTopicIds = new Set(
      system.coverage.map(({ topic_id }) => topic_id),
    );
    const omittedTopicIds = orderedTopicIds.filter(
      (topicId) => !observedTopicIds.has(topicId),
    );
    if (omittedTopicIds.length > 0 && system.coverage_default === undefined) {
      diagnostics.push({
        file: `comparison-system:${system.id}`,
        field: "coverage_default",
        message: `must declare an unverified default for ${omittedTopicIds.length} omitted taxonomy topics`,
      });
    }
  }

  if (diagnostics.length > 0) {
    throw new ComparisonTaxonomyValidationError(diagnostics);
  }
}
