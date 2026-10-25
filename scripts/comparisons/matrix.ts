import type { ComparisonTaxonomy } from "../../catalog/schema/comparison-taxonomy.js";
import type {
  ComparisonSystem,
  DepthState,
  RunBasis,
} from "../../catalog/schema/comparison.js";
export {
  depthCandidateEligibilityFields,
  selectDepthCandidates,
  type DepthCandidateEligibilityField,
  type DepthCandidateInput,
} from "../../catalog/schema/depth-candidate.js";
import { validateCoverageTopics } from "./taxonomy.js";

// 'executable-on-real-data' is not a depth state. It counts an executable or
// assessed cell only when real measured or computed records, or a genuine run on
// them, carry the runnable task, so a checker over hand-authored inputs and a
// pipeline over real data stop sharing one number. A cell whose run basis is
// unverified widens the upper bound.
export const comparisonThresholds = [
  "explained",
  "worked",
  "executable",
  "executable-on-real-data",
  "assessed",
] as const;

export type ComparisonThreshold = (typeof comparisonThresholds)[number];

type EvidenceBase = {
  access: "opened" | "inaccessible";
  evidence_id: string;
  observed_scope: string;
  reviewed_on: string;
  title: string;
  version?: string;
};

export type ComparisonEvidenceSource =
  | (EvidenceBase & {
      source_type: "url";
      url: string;
    })
  | (EvidenceBase & {
      repository_path: string;
      source_type: "repository_path";
    });

export type ComparisonMatrixRow = {
  coverage_origin: "default" | "direct";
  depth: DepthState;
  evidence: ComparisonEvidenceSource[];
  lower_at_explained: 0 | 1;
  note: string;
  provider_class: ComparisonSystem["provider_class"];
  provider_id: string;
  provider_name: string;
  reviewed_scope: string;
  run_basis: RunBasis | null;
  topic_core: boolean;
  topic_id: string;
  topic_order: number;
  topic_title: string;
  track_id: string;
  track_order: number;
  upper_at_explained: 0 | 1;
};

export type CoverageBoundsSummary = {
  absent_cells: number;
  default_unverified_cells: number;
  direct_cells: number;
  lower: number;
  provider_id: string;
  threshold: ComparisonThreshold;
  total_topics: number;
  upper: number;
};

export type ComparisonGapTopic = {
  external_providers_at_worked_or_deeper: string[];
  self_depth: DepthState;
  strongest_external_depth: Exclude<DepthState, "absent" | "unverified">;
  topic_core: boolean;
  topic_id: string;
  topic_title: string;
  track_id: string;
};

export type ComparisonSelfAuditNeededTopic = Omit<
  ComparisonGapTopic,
  "self_depth"
> & {
  self_depth: "unverified";
};

const depthRank: Record<Exclude<DepthState, "unverified">, number> = {
  absent: 0,
  mentioned: 1,
  explained: 2,
  worked: 3,
  executable: 4,
  assessed: 5,
};

function compareAscii(left: string, right: string): number {
  return left < right ? -1 : left > right ? 1 : 0;
}

export function boundsAtThreshold(
  depth: DepthState,
  threshold: ComparisonThreshold,
  runBasis: RunBasis | null = null,
): { lower: 0 | 1; upper: 0 | 1 } {
  if (depth === "unverified") {
    return { lower: 0, upper: 1 };
  }

  if (threshold === "executable-on-real-data") {
    if (depthRank[depth] < depthRank.executable) {
      return { lower: 0, upper: 0 };
    }
    if (runBasis === "real-data") {
      return { lower: 1, upper: 1 };
    }
    if (runBasis === "authored") {
      return { lower: 0, upper: 0 };
    }
    // A runnable cell without an established basis cannot count as real data, and
    // cannot be excluded from it either.
    return { lower: 0, upper: 1 };
  }

  const covered = depthRank[depth] >= depthRank[threshold] ? 1 : 0;
  return { lower: covered, upper: covered };
}

export function toEvidenceSource(
  evidence: ComparisonSystem["evidence"][number],
): ComparisonEvidenceSource {
  const base: EvidenceBase = {
    access: evidence.access,
    evidence_id: evidence.id,
    observed_scope: evidence.observed_scope,
    reviewed_on: evidence.reviewed_on,
    title: evidence.title,
    ...(evidence.version === undefined ? {} : { version: evidence.version }),
  };

  if (evidence.url !== undefined) {
    return { ...base, source_type: "url", url: evidence.url };
  }
  if (evidence.repository_path !== undefined) {
    return {
      ...base,
      repository_path: evidence.repository_path,
      source_type: "repository_path",
    };
  }
  throw new Error(`Evidence ${evidence.id} has no public source`);
}

export function buildComparisonMatrix(
  systems: ComparisonSystem[],
  taxonomy: ComparisonTaxonomy,
): ComparisonMatrixRow[] {
  validateCoverageTopics(systems, taxonomy);

  const orderedTopics = taxonomy.tracks.flatMap((track) =>
    track.topics.map((topic) => ({
      topic,
      track_id: track.id,
      track_order: track.order,
    })),
  );
  const rows: ComparisonMatrixRow[] = [];

  for (const system of [...systems].sort((left, right) =>
    compareAscii(left.id, right.id),
  )) {
    const observations = new Map(
      system.coverage.map((observation) => [observation.topic_id, observation]),
    );
    const evidenceById = new Map(
      system.evidence.map((evidence) => [evidence.id, evidence]),
    );

    for (const { topic, track_id, track_order } of orderedTopics) {
      const directObservation = observations.get(topic.id);
      const observation = directObservation ?? system.coverage_default;
      if (observation === undefined) {
        throw new Error(
          `comparison-system:${system.id}: coverage_default: no observation or explicit default for ${topic.id}`,
        );
      }

      const evidence = observation.evidence.map((evidenceId) => {
        const source = evidenceById.get(evidenceId);
        if (source === undefined) {
          throw new Error(
            `comparison-system:${system.id}: unresolved evidence ${evidenceId} for ${topic.id}`,
          );
        }
        return toEvidenceSource(source);
      });
      const explainedBounds = boundsAtThreshold(observation.depth, "explained");

      rows.push({
        coverage_origin: directObservation === undefined ? "default" : "direct",
        depth: observation.depth,
        evidence,
        lower_at_explained: explainedBounds.lower,
        note: observation.note,
        provider_class: system.provider_class,
        provider_id: system.id,
        provider_name: system.name,
        reviewed_scope: observation.reviewed_scope,
        run_basis:
          "run_basis" in observation && observation.run_basis !== undefined
            ? observation.run_basis
            : null,
        topic_core: topic.core,
        topic_id: topic.id,
        topic_order: topic.order,
        topic_title: topic.title,
        track_id,
        track_order,
        upper_at_explained: explainedBounds.upper,
      });
    }
  }

  return rows;
}

export function summarizeBounds(
  matrix: ComparisonMatrixRow[],
  threshold: ComparisonThreshold,
): Map<string, CoverageBoundsSummary> {
  const summaries = new Map<string, CoverageBoundsSummary>();

  for (const row of [...matrix].sort((left, right) =>
    compareAscii(left.provider_id, right.provider_id),
  )) {
    const bounds = boundsAtThreshold(row.depth, threshold, row.run_basis);
    const current = summaries.get(row.provider_id) ?? {
      absent_cells: 0,
      default_unverified_cells: 0,
      direct_cells: 0,
      lower: 0,
      provider_id: row.provider_id,
      threshold,
      total_topics: 0,
      upper: 0,
    };
    current.absent_cells += row.depth === "absent" ? 1 : 0;
    current.default_unverified_cells +=
      row.coverage_origin === "default" ? 1 : 0;
    current.direct_cells += row.coverage_origin === "direct" ? 1 : 0;
    current.lower += bounds.lower;
    current.total_topics += 1;
    current.upper += bounds.upper;
    summaries.set(row.provider_id, current);
  }

  return summaries;
}

export function buildGapTopics(
  matrix: ComparisonMatrixRow[],
  selfProviderId = "aidd-commons",
  // The threshold is a parameter because a deficit at one depth is invisible at
  // another: a project can sit at 'worked' on every topic and still be behind on
  // every runnable one.
  threshold: Exclude<DepthState, "absent" | "unverified"> = "worked",
): ComparisonGapTopic[] {
  const selfRows = matrix.filter(
    ({ provider_id }) => provider_id === selfProviderId,
  );
  const gapTopics: ComparisonGapTopic[] = [];

  for (const selfRow of selfRows) {
    const selfBelowThreshold =
      selfRow.depth !== "unverified" &&
      depthRank[selfRow.depth] < depthRank[threshold];
    if (!selfBelowThreshold) {
      continue;
    }

    const substantiveExternalRows = matrix.filter(
      (row) =>
        row.provider_id !== selfProviderId &&
        row.topic_id === selfRow.topic_id &&
        row.depth !== "unverified" &&
        depthRank[row.depth] >= depthRank[threshold],
    );
    if (substantiveExternalRows.length === 0) {
      continue;
    }

    const strongestExternalDepth = substantiveExternalRows.reduce(
      (strongest, row) =>
        depthRank[row.depth as Exclude<DepthState, "unverified">] >
        depthRank[strongest]
          ? (row.depth as Exclude<DepthState, "absent" | "unverified">)
          : strongest,
      substantiveExternalRows[0]!.depth as Exclude<
        DepthState,
        "absent" | "unverified"
      >,
    );

    gapTopics.push({
      external_providers_at_worked_or_deeper: substantiveExternalRows
        .map(({ provider_id }) => provider_id)
        .sort(compareAscii),
      self_depth: selfRow.depth,
      strongest_external_depth: strongestExternalDepth,
      topic_core: selfRow.topic_core,
      topic_id: selfRow.topic_id,
      topic_title: selfRow.topic_title,
      track_id: selfRow.track_id,
    });
  }

  return gapTopics;
}

export function buildSelfAuditNeededTopics(
  matrix: ComparisonMatrixRow[],
  selfProviderId = "aidd-commons",
): ComparisonSelfAuditNeededTopic[] {
  const selfRows = matrix.filter(
    (row) => row.provider_id === selfProviderId && row.depth === "unverified",
  );
  const auditNeededTopics: ComparisonSelfAuditNeededTopic[] = [];

  for (const selfRow of selfRows) {
    const substantiveExternalRows = matrix.filter(
      (row) =>
        row.provider_id !== selfProviderId &&
        row.topic_id === selfRow.topic_id &&
        row.depth !== "unverified" &&
        depthRank[row.depth] >= depthRank.worked,
    );
    if (substantiveExternalRows.length === 0) {
      continue;
    }

    const strongestExternalDepth = substantiveExternalRows.reduce(
      (strongest, row) =>
        depthRank[row.depth as Exclude<DepthState, "unverified">] >
        depthRank[strongest]
          ? (row.depth as Exclude<DepthState, "absent" | "unverified">)
          : strongest,
      substantiveExternalRows[0]!.depth as Exclude<
        DepthState,
        "absent" | "unverified"
      >,
    );

    auditNeededTopics.push({
      external_providers_at_worked_or_deeper: substantiveExternalRows
        .map(({ provider_id }) => provider_id)
        .sort(compareAscii),
      self_depth: "unverified",
      strongest_external_depth: strongestExternalDepth,
      topic_core: selfRow.topic_core,
      topic_id: selfRow.topic_id,
      topic_title: selfRow.topic_title,
      track_id: selfRow.track_id,
    });
  }

  return auditNeededTopics;
}
