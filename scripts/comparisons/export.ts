import { mkdir, readFile, writeFile } from "node:fs/promises";
import { basename, dirname, resolve } from "node:path";

import { format } from "prettier";
import { z } from "zod";

import type { ComparisonTaxonomy } from "../../catalog/schema/comparison-taxonomy.js";
import type { ComparisonSystem } from "../../catalog/schema/comparison.js";
import type {
  DepthCandidate,
  DepthCandidateSet,
} from "../../catalog/schema/depth-candidate.js";
import { loadComparisonSystems } from "./comparisons.js";
import {
  loadDepthCandidateSet,
  validateDepthCandidatesAgainstAudit,
} from "./depth-candidates.js";
import {
  buildComparisonMatrix,
  buildGapTopics,
  buildSelfAuditNeededTopics,
  comparisonThresholds,
  selectDepthCandidates,
  summarizeBounds,
  toEvidenceSource,
  type ComparisonEvidenceSource,
  type ComparisonMatrixRow,
  type ComparisonThreshold,
  type CoverageBoundsSummary,
} from "./matrix.js";
import {
  assertSecondReadings,
  loadSecondReadings,
  summarizeSecondReading,
  type SecondReadingSummary,
} from "./second-reading.js";
import { loadComparisonTaxonomy } from "./taxonomy.js";
import type { SecondReading } from "../../catalog/schema/second-reading.js";

// External provider records stopped being re-surveyed on this date. After it a
// comparator cell changes only through a source-backed correction, never through
// another round of reading one provider more closely than the others.
export const externalSurveyFrozenOn = "2026-09-11";

// ROADMAP claim-promotion gate: "most detailed" needs at least this many of the
// 18 tracks to contain a tested executable lab or an assessed capstone.
const mostDetailedRequiredTracks = 12;

const utcTimestamp = z.string().datetime({ offset: false });
const publicHttpsUrl = z
  .string()
  .url()
  .refine((value) => {
    try {
      const url = new URL(value);
      return url.protocol === "https:" && !url.username && !url.password;
    } catch {
      return false;
    }
  }, "must use HTTPS without embedded credentials");
const publicationMetadataSchema = z
  .object({
    correction_url: publicHttpsUrl.nullable(),
    correction_window_days: z.literal(30),
    first_published_at: utcTimestamp.nullable(),
    repository_url: publicHttpsUrl.nullable(),
    schema_version: z.literal("publication.v1"),
    site_url: publicHttpsUrl.nullable(),
  })
  .strict()
  .superRefine((metadata, context) => {
    const fields = [
      "first_published_at",
      "repository_url",
      "site_url",
      "correction_url",
    ] as const;
    if (fields.some((field) => metadata[field] !== null)) {
      for (const field of fields) {
        if (metadata[field] === null) {
          context.addIssue({
            code: "custom",
            path: [field],
            message:
              "must be recorded together with the publication timestamp and public URLs",
          });
        }
      }
    }
  });

export type PublicationMetadata = z.infer<typeof publicationMetadataSchema>;
export type CorrectionWindowStatus = "not_recorded" | "open" | "elapsed";
export type PublicationRecord = PublicationMetadata & {
  correction_window_ends_at: string | null;
  correction_window_status: CorrectionWindowStatus;
  status_checked_on: string | null;
};

const unpublishedMetadata: PublicationMetadata = {
  correction_url: null,
  correction_window_days: 30,
  first_published_at: null,
  repository_url: null,
  schema_version: "publication.v1",
  site_url: null,
};

function parsePublicationMetadata(
  source: unknown,
  now: Date,
): PublicationMetadata {
  if (!Number.isFinite(now.getTime())) {
    throw new Error("Invalid publication check time");
  }
  const metadata = publicationMetadataSchema.parse(source);
  if (
    metadata.first_published_at !== null &&
    new Date(metadata.first_published_at).getTime() > now.getTime()
  ) {
    throw new Error(
      "first_published_at cannot be later than the publication check time",
    );
  }
  return metadata;
}

export async function loadPublicationMetadata(
  inputPath: string,
  options: { now?: Date } = {},
): Promise<PublicationMetadata> {
  try {
    return parsePublicationMetadata(
      JSON.parse(await readFile(resolve(inputPath), "utf8")),
      options.now ?? new Date(),
    );
  } catch (error) {
    throw new Error(
      `${inputPath}: ${error instanceof Error ? error.message : String(error)}`,
    );
  }
}

export function buildPublicationRecord(
  metadata: PublicationMetadata = unpublishedMetadata,
  now = new Date(),
): PublicationRecord {
  const parsed = parsePublicationMetadata(metadata, now);
  if (parsed.first_published_at === null) {
    return {
      ...parsed,
      correction_window_ends_at: null,
      correction_window_status: "not_recorded",
      status_checked_on: null,
    };
  }
  const endsAt = new Date(
    new Date(parsed.first_published_at).getTime() +
      parsed.correction_window_days * 24 * 60 * 60 * 1000,
  );
  return {
    ...parsed,
    correction_window_ends_at: endsAt.toISOString(),
    correction_window_status: now < endsAt ? "open" : "elapsed",
    status_checked_on: now.toISOString().slice(0, 10),
  };
}

type CanonicalSource =
  | { source_type: "url"; url: string }
  | { repository_path: string; source_type: "repository_path" };

type ComparisonProvider = {
  access: ComparisonSystem["access"];
  audiences: string[];
  canonical_source: CanonicalSource;
  caveats: string[];
  evidence: ComparisonEvidenceSource[];
  id: string;
  languages: string[];
  last_verified: string;
  licenses: ComparisonSystem["licenses"];
  name: string;
  provider_class: ComparisonSystem["provider_class"];
};

export type ComparisonExportPayload = {
  as_of: string;
  claims: {
    most_comprehensive: {
      bound_condition_satisfied: boolean;
      correction_window_status: CorrectionWindowStatus;
      self_lower_at_explained: number;
      status: "not_established";
      strongest_external_upper_at_explained: number;
    };
    most_detailed: {
      bound_condition_satisfied: boolean;
      executable_or_assessed_self_tracks: number;
      real_data_executable_or_assessed_self_tracks: number;
      required_self_tracks: 12;
      self_lower_at_worked: number;
      status: "not_established";
      strongest_external_upper_at_worked: number;
    };
  };
  external_survey_frozen_on: string;
  second_readings: SecondReadingSummary[];
  gaps: {
    candidates: ReturnType<typeof buildGapTopics>;
    executable_candidates: ReturnType<typeof buildGapTopics>;
    selected_depth_candidates: DepthCandidate[];
    self_audit_needed: ReturnType<typeof buildSelfAuditNeededTopics>;
    selection_status:
      | "frozen_three_candidates"
      | "frozen_fewer_than_three_candidates"
      | "no_eligible_candidates"
      | "not_selected_missing_eligibility_records";
  };
  observations: {
    default_unverified_cells: number;
    direct_cells: number;
    total_cells: number;
  };
  providers: ComparisonProvider[];
  publication: PublicationRecord;
  rows: ComparisonMatrixRow[];
  schema_version: "comparison.v1";
  summaries: CoverageBoundsSummary[];
  taxonomy: {
    core_topics: number;
    topics: number;
    tracks: number;
    version: ComparisonTaxonomy["version"];
  };
  thresholds: ComparisonThreshold[];
};

const csvColumns: Array<keyof ComparisonMatrixRow> = [
  "provider_id",
  "provider_name",
  "provider_class",
  "track_id",
  "track_order",
  "topic_id",
  "topic_order",
  "topic_title",
  "topic_core",
  "depth",
  "run_basis",
  "coverage_origin",
  "lower_at_explained",
  "upper_at_explained",
  "reviewed_scope",
  "note",
  "evidence",
];

function compareAscii(left: string, right: string): number {
  return left < right ? -1 : left > right ? 1 : 0;
}

function canonicalSource(system: ComparisonSystem): CanonicalSource {
  if (system.canonical_url !== undefined) {
    return { source_type: "url", url: system.canonical_url };
  }
  if (system.canonical_repository_path !== undefined) {
    return {
      repository_path: system.canonical_repository_path,
      source_type: "repository_path",
    };
  }
  throw new Error(`Comparison provider ${system.id} has no canonical source`);
}

function csvValue(value: unknown): string {
  const raw = typeof value === "string" ? value : JSON.stringify(value);
  return /[",\n\r]/.test(raw) ? `"${raw.replaceAll('"', '""')}"` : raw;
}

export function comparisonRowsToCsv(rows: ComparisonMatrixRow[]): string {
  const body = rows.map((row) =>
    csvColumns.map((column) => csvValue(row[column])).join(","),
  );
  return `${csvColumns.join(",")}\n${body.join("\n")}\n`;
}

function maximum(values: number[]): number {
  return values.length === 0 ? 0 : Math.max(...values);
}

export function buildComparisonExport(
  systems: ComparisonSystem[],
  taxonomy: ComparisonTaxonomy,
  candidateSet?: DepthCandidateSet,
  secondReadings: SecondReading[] = [],
  options: { publication?: PublicationMetadata; now?: Date } = {},
): ComparisonExportPayload {
  if (systems.length === 0) {
    throw new Error("Comparison export requires at least one provider");
  }
  const publication = buildPublicationRecord(options.publication, options.now);

  const sortedSystems = [...systems].sort((left, right) =>
    compareAscii(left.id, right.id),
  );
  const rows = buildComparisonMatrix(sortedSystems, taxonomy);
  const summaries = sortedSystems.flatMap((system) =>
    comparisonThresholds.map((threshold) => {
      const summary = summarizeBounds(rows, threshold).get(system.id);
      if (summary === undefined) {
        throw new Error(
          `No ${threshold} bound summary was generated for ${system.id}`,
        );
      }
      return summary;
    }),
  );
  const summaryByProviderAndThreshold = new Map(
    summaries.map((summary) => [
      `${summary.provider_id}/${summary.threshold}`,
      summary,
    ]),
  );
  const summaryFor = (
    providerId: string,
    threshold: ComparisonThreshold,
  ): CoverageBoundsSummary => {
    const summary = summaryByProviderAndThreshold.get(
      `${providerId}/${threshold}`,
    );
    if (summary === undefined) {
      throw new Error(`Missing ${threshold} summary for ${providerId}`);
    }
    return summary;
  };

  const selfProviderId = "aidd-commons";
  const selfSystem = sortedSystems.find(({ id }) => id === selfProviderId);
  if (selfSystem === undefined) {
    throw new Error("Comparison export requires the AIDD Commons self-audit");
  }
  const externalSystems = sortedSystems.filter(
    ({ id }) => id !== selfProviderId,
  );
  const selfExplained = summaryFor(selfProviderId, "explained");
  const selfWorked = summaryFor(selfProviderId, "worked");
  const externalExplainedUpper = maximum(
    externalSystems.map(({ id }) => summaryFor(id, "explained").upper),
  );
  const externalWorkedUpper = maximum(
    externalSystems.map(({ id }) => summaryFor(id, "worked").upper),
  );
  const runnableSelfRows = rows.filter(
    (row) =>
      row.provider_id === selfProviderId &&
      (row.depth === "executable" || row.depth === "assessed"),
  );
  const executableSelfTracks = new Set(
    runnableSelfRows.map(({ track_id }) => track_id),
  ).size;
  const realDataSelfTracks = new Set(
    runnableSelfRows
      .filter(({ run_basis }) => run_basis === "real-data")
      .map(({ track_id }) => track_id),
  ).size;
  const directCells = rows.filter(
    ({ coverage_origin }) => coverage_origin === "direct",
  ).length;
  const topics = taxonomy.tracks.flatMap(({ topics: trackTopics }) =>
    trackTopics.map((topic) => topic),
  );
  const gapCandidates = buildGapTopics(rows, selfProviderId);
  // Reported separately because the worked-threshold table cannot see a topic
  // where this project is at 'worked' and a provider is already runnable.
  const executableGaps = buildGapTopics(rows, selfProviderId, "executable");
  if (candidateSet !== undefined) {
    validateDepthCandidatesAgainstAudit(
      candidateSet,
      gapCandidates,
      taxonomy,
      rows,
    );
  }
  const selectedDepthCandidates = selectDepthCandidates(
    candidateSet?.candidates ?? [],
  );
  const selectionStatus =
    candidateSet === undefined
      ? "not_selected_missing_eligibility_records"
      : selectedDepthCandidates.length === 0
        ? "no_eligible_candidates"
        : selectedDepthCandidates.length === 3
          ? "frozen_three_candidates"
          : "frozen_fewer_than_three_candidates";

  return {
    as_of: [
      ...systems.map(({ last_verified }) => last_verified),
      ...(candidateSet === undefined ? [] : [candidateSet.as_of]),
    ]
      .sort(compareAscii)
      .at(-1)!,
    claims: {
      most_comprehensive: {
        bound_condition_satisfied:
          externalSystems.length > 0 &&
          externalSystems.every(
            ({ id }) => selfExplained.lower > summaryFor(id, "explained").upper,
          ),
        correction_window_status: publication.correction_window_status,
        self_lower_at_explained: selfExplained.lower,
        status: "not_established",
        strongest_external_upper_at_explained: externalExplainedUpper,
      },
      most_detailed: {
        // The two measurable conditions of the claim-promotion gate for "most
        // detailed": enough runnable or assessed tracks, and a worked-or-deeper
        // lower bound that exceeds every comparator's upper bound. The claim
        // itself also needs the public correction window, so status stays fixed.
        bound_condition_satisfied:
          executableSelfTracks >= mostDetailedRequiredTracks &&
          externalSystems.length > 0 &&
          externalSystems.every(
            ({ id }) => selfWorked.lower > summaryFor(id, "worked").upper,
          ),
        executable_or_assessed_self_tracks: executableSelfTracks,
        real_data_executable_or_assessed_self_tracks: realDataSelfTracks,
        required_self_tracks: mostDetailedRequiredTracks,
        self_lower_at_worked: selfWorked.lower,
        status: "not_established",
        strongest_external_upper_at_worked: externalWorkedUpper,
      },
    },
    external_survey_frozen_on: externalSurveyFrozenOn,
    second_readings: secondReadings.map((reading) => {
      const system = sortedSystems.find(({ id }) => id === reading.system_id);
      if (system === undefined) {
        throw new Error(`Second reading ${reading.id} names no provider`);
      }
      return summarizeSecondReading(system, reading);
    }),
    gaps: {
      candidates: gapCandidates,
      selected_depth_candidates: selectedDepthCandidates,
      executable_candidates: executableGaps,
      self_audit_needed: buildSelfAuditNeededTopics(rows, selfProviderId),
      selection_status: selectionStatus,
    },
    observations: {
      default_unverified_cells: rows.length - directCells,
      direct_cells: directCells,
      total_cells: rows.length,
    },
    providers: sortedSystems.map((system) => ({
      access: system.access,
      audiences: system.audiences,
      canonical_source: canonicalSource(system),
      caveats: system.caveats,
      evidence: system.evidence.map(toEvidenceSource),
      id: system.id,
      languages: system.languages,
      last_verified: system.last_verified,
      licenses: system.licenses,
      name: system.name,
      provider_class: system.provider_class,
    })),
    publication,
    rows,
    schema_version: "comparison.v1",
    summaries,
    taxonomy: {
      core_topics: topics.filter(({ core }) => core).length,
      topics: topics.length,
      tracks: taxonomy.tracks.length,
      version: taxonomy.version,
    },
    thresholds: [...comparisonThresholds],
  };
}

function boundText(
  payload: ComparisonExportPayload,
  providerId: string,
  threshold: ComparisonThreshold,
): string {
  const summary = payload.summaries.find(
    (candidate) =>
      candidate.provider_id === providerId && candidate.threshold === threshold,
  );
  if (summary === undefined) {
    throw new Error(`Missing ${threshold} audit summary for ${providerId}`);
  }
  return summary.lower === summary.upper
    ? String(summary.lower)
    : `${summary.lower}-${summary.upper}`;
}

function markdownValue(value: string): string {
  return value.replaceAll("|", "\\|").replaceAll("\n", " ");
}

export async function renderComparisonAudit(
  payload: ComparisonExportPayload,
): Promise<string> {
  const providerRows = payload.providers.map((provider) => {
    const explainedSummary = payload.summaries.find(
      (summary) =>
        summary.provider_id === provider.id &&
        summary.threshold === "explained",
    );
    if (explainedSummary === undefined) {
      throw new Error(`Missing explained summary for ${provider.id}`);
    }
    return `| ${markdownValue(provider.name)} | ${provider.provider_class} | ${explainedSummary.direct_cells} | ${explainedSummary.absent_cells} | ${explainedSummary.default_unverified_cells} | ${boundText(payload, provider.id, "explained")} | ${boundText(payload, provider.id, "worked")} | ${boundText(payload, provider.id, "executable")} | ${boundText(payload, provider.id, "executable-on-real-data")} | ${boundText(payload, provider.id, "assessed")} |`;
  });
  const secondReadingSections = payload.second_readings.map((summary) => {
    const thresholdRows = summary.thresholds.map(
      ({ threshold, recorded, reading }) =>
        `| ${threshold} | ${recorded} | ${reading} |`,
    );
    return `Reading \`${summary.id}\`, ${summary.reviewed_on}, of commit${summary.commits.length === 1 ? "" : "s"} ${summary.commits.map((commit) => `\`${commit}\``).join(", ")}. ${markdownValue(summary.reviewer)}

Of ${summary.cells} topics, the recorded depth equals the independent reading on ${summary.equal}, and the reading is deeper on ${summary.reading_deeper}. It is shallower on ${summary.reading_shallower}, and the validator refuses any record where it is shallower, so a topic this project claims more on than the reading supports cannot be published.

| Threshold | Recorded here | Independent reading |
| --------- | ------------- | ------------------- |
${thresholdRows.join("\n")}`;
  });
  const realDataSelf = boundText(
    payload,
    "aidd-commons",
    "executable-on-real-data",
  );
  const realDataExternal = payload.summaries.filter(
    (summary) =>
      summary.threshold === "executable-on-real-data" &&
      summary.provider_id !== "aidd-commons",
  );
  const realDataExternalLower = Math.max(
    ...realDataExternal.map((summary) => summary.lower),
  );
  const realDataExternalUpper = Math.max(
    ...realDataExternal.map((summary) => summary.upper),
  );
  const gapRows = payload.gaps.candidates.map(
    (gap) =>
      `| ${gap.track_id} | ${gap.topic_id} | ${markdownValue(gap.topic_title)} | ${gap.self_depth} | ${gap.strongest_external_depth} | ${gap.external_providers_at_worked_or_deeper.join(", ")} |`,
  );
  const executableGapRows = payload.gaps.executable_candidates.map(
    (gap) =>
      `| ${gap.track_id} | ${gap.topic_id} | ${markdownValue(gap.topic_title)} | ${gap.self_depth} | ${gap.strongest_external_depth} | ${gap.external_providers_at_worked_or_deeper.join(", ")} |`,
  );
  const auditNeededRows = payload.gaps.self_audit_needed.map(
    (gap) =>
      `| ${gap.track_id} | ${gap.topic_id} | ${markdownValue(gap.topic_title)} | ${gap.strongest_external_depth} | ${gap.external_providers_at_worked_or_deeper.join(", ")} |`,
  );
  const depthCandidateRows = payload.gaps.selected_depth_candidates.map(
    (candidate, index) =>
      `| ${index + 1} | ${candidate.implementation.status} | ${candidate.track_id} | ${candidate.topic_id} | ${markdownValue(candidate.topic_title)} | ${markdownValue(`${candidate.data_feasibility.dataset_name} (${candidate.data_feasibility.dataset_version})`)} | ${markdownValue(`${candidate.independent_unit.name} (n=${candidate.independent_unit.observed_units})`)} | ${markdownValue(candidate.cheap_baseline.name)} | ${markdownValue(candidate.evaluation.primary_metric)} | ${candidate.compute.estimated_runtime_minutes} min CPU; ${candidate.compute.estimated_memory_gb} GB RAM; ${candidate.compute.estimated_download_mb} MB download | ${markdownValue(candidate.licence.name)} |`,
  );
  const depthSelectionSummary =
    payload.gaps.selected_depth_candidates.length === 3
      ? "Three v0.2b depth candidates were selected after passing all seven frozen eligibility criteria and are ranked below."
      : payload.gaps.selected_depth_candidates.length === 0
        ? "No candidate passes all seven frozen eligibility criteria. The criteria were not weakened."
        : `${payload.gaps.selected_depth_candidates.length} v0.2b depth candidates were selected after passing all seven frozen eligibility criteria. The criteria were not weakened to fill the tranche.`;
  const confirmedGapCount = payload.gaps.candidates.length;
  const confirmedGapNoun = confirmedGapCount === 1 ? "depth gap" : "depth gaps";
  const confirmedGapVerb = confirmedGapCount === 1 ? "has" : "have";
  const publication = payload.publication;
  const correctionWindowSummary =
    publication.first_published_at === null
      ? "No public correction window has been recorded."
      : `First publication was recorded at ${publication.first_published_at}. The public ${publication.correction_window_days}-day correction window ends at ${publication.correction_window_ends_at}; its status was ${publication.correction_window_status} when checked on ${publication.status_checked_on} (UTC). Submit source-backed corrections through [the public correction route](${publication.correction_url}). Elapsed time alone does not establish either claim; submitted corrections and the other claim conditions still need review.`;

  const markdown = `# AIDD Commons comparison audit

As of: ${payload.as_of}

## Result

Claim status: not established.

- The frozen audit contains ${payload.providers.length} providers, ${payload.taxonomy.tracks} tracks, and ${payload.taxonomy.topics} topics.
- It materializes ${payload.observations.total_cells} provider-topic cells: ${payload.observations.direct_cells} direct observations and ${payload.observations.default_unverified_cells} explicit-default unknown cells.
- AIDD Commons has an explained-or-deeper lower bound of ${payload.claims.most_comprehensive.self_lower_at_explained}; the strongest external upper bound is ${payload.claims.most_comprehensive.strongest_external_upper_at_explained}.
- ${absenceProvenance(payload)}
- ${confirmedGapCount} confirmed ${confirmedGapNoun} ${confirmedGapVerb} direct AIDD Commons evidence; ${payload.gaps.self_audit_needed.length} additional topics require self-audit before gap classification.
- ${payload.gaps.executable_candidates.length} topics are below 'executable' here while an external provider is already runnable there.
- Runnable coverage on real data is ${realDataSelf} topics here. On the same threshold the largest external lower bound is ${realDataExternalLower} and the largest external upper bound is ${realDataExternalUpper}, so unresolved cells still decide that comparison.
- External provider records have not been re-surveyed since ${payload.external_survey_frozen_on}. This project's own row is checked against an independent second reading and may not claim more than it.
- ${depthSelectionSummary}

The evidence does not support either a "world's most comprehensive" or a
"most detailed" claim. Unknown cells remain in upper bounds. Both claim statuses
remain not established pending review of the correction window and all other
claim conditions.

## Public correction window

${correctionWindowSummary}

## Method

Every provider is crossed with every taxonomy topic. Direct observations take
precedence over the record's explicit 'coverage_default: unverified'. An
'unverified' cell contributes zero to the lower bound and one to the upper
bound. An 'absent' cell contributes zero to both. Observed depth states are
evaluated independently at 'explained', 'worked', 'executable', and 'assessed'
thresholds. No composite or weighted total is calculated.

Every executable or assessed cell also records what its runnable task rests on.
'real-data' means measured or computed records that exist independently of the
course, or a genuine simulation, docking or structure-prediction run on them.
'authored' means hand-written or synthetic inputs, including real molecules with
invented values. 'unverified' means the record does not establish which. The
'executable on real data' column counts only 'real-data' cells; an 'unverified'
one adds to the upper bound alone. External cells were classified only from what
each cell's own note, reviewed scope and evidence titles state, and no provider
was re-read to classify them.

## Coverage bounds

Values are lower-upper counts. A single number means that the two bounds are
equal.

| Provider | Class | Direct cells | Recorded absent | Default unknown | Explained | Worked | Executable | Executable on real data | Assessed |
| -------- | ----- | ------------ | --------------- | --------------- | --------- | ------ | ---------- | ----------------------- | -------- |
${providerRows.join("\n")}

## Claim checks

| Claim | Status | Decisive current evidence |
| ----- | ------ | -------------------------- |
| World's most comprehensive open AIDD learning system | not established | Explained lower bound ${payload.claims.most_comprehensive.self_lower_at_explained}; strongest external upper bound ${payload.claims.most_comprehensive.strongest_external_upper_at_explained}; bound condition ${payload.claims.most_comprehensive.bound_condition_satisfied ? "met" : "not met"}; correction window ${payload.claims.most_comprehensive.correction_window_status}. |
| Most detailed AIDD learning system | not established | ${payload.claims.most_detailed.executable_or_assessed_self_tracks} of the required ${payload.claims.most_detailed.required_self_tracks} self-audit tracks contain executable or assessed coverage, ${payload.claims.most_detailed.real_data_executable_or_assessed_self_tracks} of them on real data; worked lower bound ${payload.claims.most_detailed.self_lower_at_worked}; strongest external upper bound ${payload.claims.most_detailed.strongest_external_upper_at_worked}; bound condition ${payload.claims.most_detailed.bound_condition_satisfied ? "met" : "not met"}; correction window ${payload.claims.most_comprehensive.correction_window_status}. |

## Independent second reading of this project's row

The row above is scored by the same hand that wrote the lessons. A reviewer that
never saw those scores read the committed material and scored every topic again.
Its 'assessed' needs only an answered exercise, while this audit lets 'assessed'
claim 'executable', so a reading of 'assessed' with nothing runnable is compared
here as 'worked'. Where the two disagreed, the shallower one was recorded, and a
record is raised to the depth a reading has already verified rather than past
it. It is an automated reading of teaching depth, not reader evidence.

${secondReadingSections.length === 0 ? "No independent reading is recorded." : secondReadingSections.join("\n\n")}

## Confirmed depth gaps

These rows show topics where AIDD Commons is below 'worked' and at least one
external provider has direct 'worked', 'executable', or 'assessed' evidence.
Both sides have direct depth evidence. Frozen selection status is reported in
the following section rather than inferred from this table.

| Track | Topic | Title | AIDD Commons | Strongest external depth | External providers at worked or deeper |
| ----- | ----- | ----- | ------------ | ------------------------ | -------------------------------------- |
${gapRows.length === 0 ? "| - | - | No evidence-backed gap identified | - | - | - |" : gapRows.join("\n")}

## Confirmed executable gaps

These rows show topics where AIDD Commons is below 'executable' and at least one
external provider has direct 'executable' or 'assessed' evidence. The table
above cannot show them, because a topic where this project is at 'worked' and a
provider is already runnable is not below the worked threshold. Teaching a
decision on paper and letting a reader run it are different deliverables, and
this project is behind on the second.

| Track | Topic | Title | AIDD Commons | Strongest external depth | External providers at executable or deeper |
| ----- | ----- | ----- | ------------ | ------------------------ | ------------------------------------------ |
${executableGapRows.length === 0 ? "| - | - | No evidence-backed executable gap identified | - | - | - |" : executableGapRows.join("\n")}

## Frozen v0.2b depth candidates

Selection status: \`${payload.gaps.selection_status}\`.

${depthSelectionSummary} Ranking uses transitive downstream prerequisite value,
then lower maintenance burden, then topic ID. The selection fields are frozen
snapshots; implementation status can advance without rewriting why a candidate
was selected. Data-feasibility counts are not model performance or test results.

| Rank | Status | Track | Topic | Title | Dataset and version | Independent unit | Cheap baseline | Primary metric | CPU estimate | Licence |
| ---- | ------ | ----- | ----- | ----- | ------------------- | ---------------- | -------------- | -------------- | ------------ | ------- |
${depthCandidateRows.length === 0 ? "| - | - | - | - | No candidate passed all criteria | - | - | - | - | - | - |" : depthCandidateRows.join("\n")}

## Self-audit needed before gap classification

For these topics, at least one external provider has worked-or-deeper evidence,
but the AIDD Commons cell is 'unverified'. They are audit priorities, not
confirmed deficiencies and not eligible for depth-candidate selection.

| Track | Topic | Title | Strongest external depth | External providers at worked or deeper |
| ----- | ----- | ----- | ------------------------ | -------------------------------------- |
${auditNeededRows.length === 0 ? "| - | - | No additional self-audit priority identified | - | - |" : auditNeededRows.join("\n")}

## Limitations

- The 12 external systems are a frozen first comparison set, not an exhaustive multilingual census.
- ${payload.observations.default_unverified_cells} cells remain unknown. They cannot support an absence claim or a promoted comparative claim.
- 'executable' describes a directly visible runnable task surface. It does not mean this audit reran every external notebook.
- T05 primary evaluation and assay replication are completed; see [the lab and reviewed results](../labs/chembl_egfr/README.md). T15 previously accessed shared labels, so this is not an entirely untouched independent confirmatory evaluation. The descriptor choice reached the frozen grid's upper edge. The assay-level failure is retained separately from the primary result; no pooled superiority claim is made.
- Candidate-selection fields are historical, not current run status. Read each candidate's implementation note for current delivery, including the completed T11 benzene and uracil evaluations. The selection-time \`not_run\` text is preserved as history.
- Licences apply only to the scopes stated in each provider record. Upstream datasets, services, weights, and solution materials may have separate terms.
- Corrections require source-backed record changes followed by deterministic regeneration of this report and the JSON and CSV projections.
`;

  return format(markdown, { parser: "markdown" });
}

type CliOptions = {
  audit: string;
  candidates: string;
  output: string;
  publication: string;
  reviews: string;
  systems: string;
  taxonomy: string;
  today?: string;
  now?: string;
};

function parseArguments(argumentsList: string[]): CliOptions {
  const options: CliOptions = {
    audit: "docs/COMPARISON_AUDIT.md",
    candidates: "catalog/comparisons/depth-candidates.yaml",
    output: "site/public/data",
    publication: "catalog/comparisons/publication.json",
    reviews: "catalog/comparisons/reviews",
    systems: "catalog/comparisons/systems",
    taxonomy: "catalog/comparisons/taxonomy.yaml",
  };

  for (let index = 0; index < argumentsList.length; index += 1) {
    const argument = argumentsList[index];
    if (
      argument === "--audit" ||
      argument === "--candidates" ||
      argument === "--output" ||
      argument === "--publication" ||
      argument === "--reviews" ||
      argument === "--systems" ||
      argument === "--taxonomy" ||
      argument === "--today" ||
      argument === "--now"
    ) {
      const value = argumentsList[index + 1];
      if (value === undefined) {
        throw new Error(`${argument} requires a value`);
      }
      const key = argument.slice(2) as keyof CliOptions;
      options[key] = value;
      index += 1;
    } else {
      throw new Error(`Unknown argument: ${argument}`);
    }
  }

  return options;
}

async function main(): Promise<void> {
  const options = parseArguments(process.argv.slice(2));
  const now =
    options.now === undefined
      ? new Date()
      : new Date(utcTimestamp.parse(options.now));
  const [systems, taxonomy, candidateSet, readings, publication] =
    await Promise.all([
      loadComparisonSystems(options.systems, { today: options.today }),
      loadComparisonTaxonomy(options.taxonomy),
      loadDepthCandidateSet(options.candidates, { today: options.today }),
      loadSecondReadings(options.reviews),
      loadPublicationMetadata(options.publication, { now }),
    ]);
  assertSecondReadings(systems, readings, taxonomy);
  const payload = buildComparisonExport(
    systems,
    taxonomy,
    candidateSet,
    readings.map(({ reading }) => reading),
    { publication, now },
  );
  const outputDirectory = resolve(options.output);
  const auditPath = resolve(options.audit);
  const audit = await renderComparisonAudit(payload);

  await Promise.all([
    mkdir(outputDirectory, { recursive: true }),
    mkdir(dirname(auditPath), { recursive: true }),
  ]);
  await Promise.all([
    writeFile(
      `${outputDirectory}/comparison.v1.json`,
      `${JSON.stringify(payload, null, 2)}\n`,
    ),
    writeFile(
      `${outputDirectory}/comparison.v1.csv`,
      comparisonRowsToCsv(payload.rows),
    ),
    writeFile(auditPath, audit),
  ]);

  console.log(`Exported ${payload.rows.length} comparison cells.`);
}

const invokedAsCli =
  process.argv[1] !== undefined && basename(process.argv[1]) === "export.ts";

if (invokedAsCli) {
  main().catch((error: unknown) => {
    console.error(error instanceof Error ? error.message : String(error));
    process.exitCode = 1;
  });
}

// A comparator's upper bound falls whenever this project records a direct
// observation that sits below the threshold, whether that is 'absent' or any
// depth shallower than the threshold. Both are ceilings lowered by our own
// review, so the comparison is movable by the same hand that reports it and the
// counterfactual is published beside the result.
function absenceProvenance(payload: ComparisonExportPayload): string {
  const external = payload.summaries.filter(
    (summary) =>
      summary.threshold === "explained" &&
      summary.provider_id !== "aidd-commons",
  );
  const externalIds = new Set(external.map((summary) => summary.provider_id));
  const loweredByReview = payload.rows.filter(
    (row) =>
      externalIds.has(row.provider_id) &&
      row.coverage_origin === "direct" &&
      row.upper_at_explained === 0,
  ).length;
  const providersTouched = new Set(
    payload.rows
      .filter(
        (row) =>
          externalIds.has(row.provider_id) &&
          row.coverage_origin === "direct" &&
          row.upper_at_explained === 0,
      )
      .map((row) => row.provider_id),
  ).size;
  const withoutReview = Math.max(
    ...external.map(
      (summary) =>
        summary.upper +
        payload.rows.filter(
          (row) =>
            row.provider_id === summary.provider_id &&
            row.coverage_origin === "direct" &&
            row.upper_at_explained === 0,
        ).length,
    ),
  );
  return `Comparator ceilings at 'explained' were lowered by ${loweredByReview} cells this project reviewed and found below that threshold, across ${providersTouched} providers. Had none of them been reviewed, the strongest external upper bound would be ${withoutReview}.`;
}
