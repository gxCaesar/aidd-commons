import { readFile } from "node:fs/promises";
import { relative, resolve } from "node:path";

import { parse } from "yaml";

import type { ComparisonTaxonomy } from "../../catalog/schema/comparison-taxonomy.js";
import {
  depthCandidateEligibilityFields,
  depthCandidateSetSchema,
  selectDepthCandidates,
  type DepthCandidateSet,
} from "../../catalog/schema/depth-candidate.js";
import {
  isCalendarDate,
  latestCurrentCalendarDate,
} from "../../catalog/schema/resource.js";
import type { ComparisonGapTopic, ComparisonMatrixRow } from "./matrix.js";

export type DepthCandidateDiagnostic = {
  field: string;
  file: string;
  message: string;
};

function formatDiagnostic(diagnostic: DepthCandidateDiagnostic): string {
  return `${diagnostic.file}: ${diagnostic.field}: ${diagnostic.message}`;
}

export class DepthCandidateValidationError extends Error {
  constructor(readonly diagnostics: DepthCandidateDiagnostic[]) {
    super(diagnostics.map(formatDiagnostic).join("\n"));
    this.name = "DepthCandidateValidationError";
  }
}

export async function loadDepthCandidateSet(
  inputPath: string,
  options: { today?: string } = {},
): Promise<DepthCandidateSet> {
  const input = resolve(inputPath);
  const file = relative(process.cwd(), input) || input;
  const today = options.today ?? latestCurrentCalendarDate();
  if (!isCalendarDate(today)) {
    throw new Error(`Invalid validator date: ${today}`);
  }

  let source: unknown;
  try {
    source = parse(await readFile(input, "utf8"));
  } catch (error) {
    throw new DepthCandidateValidationError([
      {
        file,
        field: "$yaml",
        message:
          error instanceof Error ? error.message : "could not parse YAML",
      },
    ]);
  }

  const result = depthCandidateSetSchema.safeParse(source);
  if (!result.success) {
    throw new DepthCandidateValidationError(
      result.error.issues.map((issue) => ({
        file,
        field: issue.path.map(String).join(".") || "$record",
        message: issue.message,
      })),
    );
  }

  const diagnostics: DepthCandidateDiagnostic[] = [];
  if (result.data.as_of > today) {
    diagnostics.push({
      file,
      field: "as_of",
      message: `cannot be later than validator date ${today}`,
    });
  }
  for (const [index, candidate] of result.data.candidates.entries()) {
    if (candidate.last_verified > today) {
      diagnostics.push({
        file,
        field: `candidates.${index}.last_verified`,
        message: `cannot be later than validator date ${today}`,
      });
    }
  }
  if (diagnostics.length > 0) {
    throw new DepthCandidateValidationError(diagnostics);
  }

  return result.data;
}

function compareArrays(left: string[], right: string[]): boolean {
  return (
    left.length === right.length &&
    left.every((value, index) => value === right[index])
  );
}

export function prerequisiteValue(
  taxonomy: ComparisonTaxonomy,
  prerequisiteTopicId: string,
): number {
  const topics = taxonomy.tracks.flatMap(({ topics: trackTopics }) =>
    trackTopics.map((topic) => topic),
  );
  const prerequisitesByTopic = new Map(
    topics.map((topic) => [topic.id, topic.prerequisites]),
  );

  return topics.filter((topic) => {
    const pending = [...topic.prerequisites];
    const visited = new Set<string>();
    while (pending.length > 0) {
      const prerequisite = pending.pop()!;
      if (prerequisite === prerequisiteTopicId) {
        return true;
      }
      if (visited.has(prerequisite)) {
        continue;
      }
      visited.add(prerequisite);
      pending.push(...(prerequisitesByTopic.get(prerequisite) ?? []));
    }
    return false;
  }).length;
}

export function validateDepthCandidatesAgainstAudit(
  record: DepthCandidateSet,
  gaps: ComparisonGapTopic[],
  taxonomy: ComparisonTaxonomy,
  matrix: ComparisonMatrixRow[],
): void {
  const file = "catalog/comparisons/depth-candidates.yaml";
  const diagnostics: DepthCandidateDiagnostic[] = [];
  const gapByTopic = new Map(gaps.map((gap) => [gap.topic_id, gap]));
  const taxonomyTopicById = new Map(
    taxonomy.tracks.flatMap((track) =>
      track.topics.map(
        (topic) =>
          [
            topic.id,
            {
              topic_core: topic.core,
              topic_title: topic.title,
              track_id: track.id,
            },
          ] as const,
      ),
    ),
  );
  const currentSelfDepthByTopic = new Map(
    matrix
      .filter(({ provider_id }) => provider_id === "aidd-commons")
      .map(({ depth, topic_id }) => [topic_id, depth]),
  );
  const depthRank = {
    absent: 0,
    mentioned: 1,
    explained: 2,
    worked: 3,
    executable: 4,
    assessed: 5,
    unverified: -1,
  } as const;

  for (const [index, candidate] of record.candidates.entries()) {
    const prefix = `candidates.${index}`;
    const gap = gapByTopic.get(candidate.topic_id);
    const taxonomyTopic = taxonomyTopicById.get(candidate.topic_id);
    const currentSelfDepth = currentSelfDepthByTopic.get(candidate.topic_id);
    if (gap === undefined) {
      if (candidate.implementation.status === "planned") {
        diagnostics.push({
          file,
          field: `${prefix}.implementation.status`,
          message:
            "must leave planned after implementation begins and the current self-audit is no longer a confirmed gap",
        });
      }
      if (
        currentSelfDepth === undefined ||
        depthRank[currentSelfDepth] < depthRank.worked
      ) {
        diagnostics.push({
          file,
          field: `${prefix}.topic_id`,
          message:
            "is not a current confirmed gap and lacks worked-or-deeper AIDD Commons evidence",
        });
      }
    } else {
      for (const field of [
        "track_id",
        "topic_title",
        "topic_core",
        "self_depth",
        "strongest_external_depth",
      ] as const) {
        if (candidate[field] !== gap[field]) {
          diagnostics.push({
            file,
            field: `${prefix}.${field}`,
            message: `does not match the generated gap value ${String(gap[field])}`,
          });
        }
      }

      if (
        !compareArrays(
          candidate.external_providers_at_worked_or_deeper,
          gap.external_providers_at_worked_or_deeper,
        )
      ) {
        diagnostics.push({
          file,
          field: `${prefix}.external_providers_at_worked_or_deeper`,
          message: "does not match the generated gap providers in ASCII order",
        });
      }
    }

    if (taxonomyTopic === undefined) {
      diagnostics.push({
        file,
        field: `${prefix}.topic_id`,
        message: "does not resolve to a current taxonomy topic",
      });
    } else {
      for (const field of ["track_id", "topic_title", "topic_core"] as const) {
        if (candidate[field] !== taxonomyTopic[field]) {
          diagnostics.push({
            file,
            field: `${prefix}.${field}`,
            message: `does not match the current taxonomy value ${String(taxonomyTopic[field])}`,
          });
        }
      }
    }

    if (
      candidate.implementation.status === "completed" &&
      (currentSelfDepth === undefined ||
        depthRank[currentSelfDepth] < depthRank.assessed)
    ) {
      diagnostics.push({
        file,
        field: `${prefix}.implementation.status`,
        message: "completed requires assessed current AIDD Commons evidence",
      });
    }

    const expectedPrerequisiteValue = prerequisiteValue(
      taxonomy,
      candidate.topic_id,
    );
    if (candidate.prerequisite_value !== expectedPrerequisiteValue) {
      diagnostics.push({
        file,
        field: `${prefix}.prerequisite_value`,
        message: `must equal the taxonomy-derived transitive downstream count ${expectedPrerequisiteValue}`,
      });
    }

    for (const eligibilityField of depthCandidateEligibilityFields) {
      if (candidate.eligibility[eligibilityField] !== true) {
        diagnostics.push({
          file,
          field: `${prefix}.eligibility.${eligibilityField}`,
          message: "must be true for a frozen depth candidate",
        });
      }
    }
  }

  const rankedIds = selectDepthCandidates(record.candidates).map(
    ({ topic_id }) => topic_id,
  );
  const declaredIds = record.candidates.map(({ topic_id }) => topic_id);
  if (!compareArrays(declaredIds, rankedIds)) {
    diagnostics.push({
      file,
      field: "candidates",
      message:
        "must contain at most three fully eligible candidates in frozen ranking order",
    });
  }

  if (diagnostics.length > 0) {
    throw new DepthCandidateValidationError(diagnostics);
  }
}
