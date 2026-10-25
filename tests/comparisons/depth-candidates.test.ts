import { readFile } from "node:fs/promises";
import { fileURLToPath } from "node:url";

import { parse } from "yaml";
import { describe, expect, it } from "vitest";

import {
  depthCandidateSetSchema,
  selectDepthCandidates,
  type DepthCandidate,
} from "../../catalog/schema/depth-candidate.js";
import { loadComparisonSystems } from "../../scripts/comparisons/comparisons.js";
import {
  loadDepthCandidateSet,
  validateDepthCandidatesAgainstAudit,
} from "../../scripts/comparisons/depth-candidates.js";
import {
  buildComparisonMatrix,
  buildGapTopics,
} from "../../scripts/comparisons/matrix.js";
import { loadComparisonTaxonomy } from "../../scripts/comparisons/taxonomy.js";
import { latestCurrentCalendarDate } from "../../catalog/schema/resource.js";

const repositoryRoot = fileURLToPath(new URL("../..", import.meta.url));

const allEligible = {
  data_feasibility: true,
  cheap_baseline: true,
  independent_unit: true,
  evaluation: true,
  licence: true,
  compute: true,
  safety: true,
} as const;

const candidate: DepthCandidate = {
  topic_id: "topic-one",
  track_id: "track-one",
  topic_title: "Topic one",
  topic_core: true,
  self_depth: "explained",
  strongest_external_depth: "executable",
  external_providers_at_worked_or_deeper: ["provider-one"],
  prerequisite_value: 2,
  implementation: {
    status: "planned",
    updated_on: "2026-09-05",
    note: "The frozen candidate has not entered implementation.",
  },
  maintenance: {
    burden: 1,
    rationale: "The inputs and baseline have stable public interfaces.",
  },
  eligibility: allEligible,
  data_feasibility: {
    dataset_name: "Example dataset",
    dataset_version: "v1",
    source_url: "https://example.org/data",
    entity_unit: "molecule",
    inputs: ["canonical SMILES"],
    labels: ["measured endpoint"],
    observed_entities: 10,
    evidence: ["dataset"],
  },
  cheap_baseline: {
    name: "Fingerprint Ridge",
    protocol: "Fit a fixed Ridge model on training molecules only.",
  },
  independent_unit: {
    name: "molecular scaffold",
    observed_units: 4,
    note: "Repeated measurements of one molecule are not independent units.",
  },
  evaluation: {
    split: "Fixed scaffold-disjoint train, validation, and test partitions.",
    primary_metric: "MAE",
    secondary_metrics: ["RMSE"],
    independent_validation: "A separately sourced assay is held out.",
  },
  licence: {
    name: "CC BY-SA 3.0",
    scope: "Dataset content",
    evidence: ["licence"],
  },
  compute: {
    device: "cpu",
    estimated_download_mb: 1,
    estimated_memory_gb: 2,
    estimated_runtime_minutes: 10,
    basis: "A small tabular dataset and fixed linear baseline.",
  },
  safety: {
    disposition: "safe_non_operational",
    rationale:
      "The exercise uses existing measurements and no synthesis instructions.",
  },
  evidence: [
    {
      id: "dataset",
      url: "https://example.org/data",
      title: "Dataset record",
      observed_scope: "The record exposes versioned inputs and labels.",
      access: "opened",
      reviewed_on: "2026-09-05",
    },
    {
      id: "licence",
      url: "https://example.org/licence",
      title: "Dataset licence",
      observed_scope: "The licence covers the dataset content.",
      access: "opened",
      reviewed_on: "2026-09-05",
    },
  ],
  last_verified: "2026-09-05",
};

describe("frozen v0.2b depth candidates", () => {
  it("selects no candidate with unresolved data or licence eligibility", () => {
    const unresolvedData: DepthCandidate = {
      ...candidate,
      eligibility: { ...allEligible, data_feasibility: "unverified" },
    };
    const unresolvedLicence: DepthCandidate = {
      ...candidate,
      eligibility: { ...allEligible, licence: "unverified" },
    };

    expect(selectDepthCandidates([unresolvedData])).toEqual([]);
    expect(selectDepthCandidates([unresolvedLicence])).toEqual([]);
  });

  it("requires the named data, unit, evaluation, licence, compute, and safety contract", () => {
    expect(
      depthCandidateSetSchema.safeParse({
        version: "0.2b-candidates.v1",
        selection_rule: "roadmap-v0.2-2026-09-04",
        as_of: "2026-09-05",
        candidates: [candidate],
      }).success,
    ).toBe(true);

    const incomplete = structuredClone(candidate) as Record<string, unknown>;
    delete incomplete.evaluation;
    expect(
      depthCandidateSetSchema.safeParse({
        version: "0.2b-candidates.v1",
        selection_rule: "roadmap-v0.2-2026-09-04",
        as_of: "2026-09-05",
        candidates: [incomplete],
      }).success,
    ).toBe(false);

    expect(
      depthCandidateSetSchema.safeParse({
        version: "0.2b-candidates.v1",
        selection_rule: "roadmap-v0.2-2026-09-04",
        as_of: "2026-09-05",
        candidates: [{ ...candidate, model_performance: { mae: 0.1 } }],
      }).success,
    ).toBe(false);

    const mismatchedSource = structuredClone(candidate);
    mismatchedSource.data_feasibility.source_url =
      "https://example.org/unreferenced-data";
    expect(
      depthCandidateSetSchema.safeParse({
        version: "0.2b-candidates.v1",
        selection_rule: "roadmap-v0.2-2026-09-04",
        as_of: "2026-09-05",
        candidates: [mismatchedSource],
      }).success,
    ).toBe(false);
  });

  it("freezes no more than three fully eligible, result-free candidates", async () => {
    const source = parse(
      await readFile(
        `${repositoryRoot}/catalog/comparisons/depth-candidates.yaml`,
        "utf8",
      ),
    ) as unknown;
    const record = depthCandidateSetSchema.parse(source);
    const selected = selectDepthCandidates(record.candidates);

    expect(selected).toHaveLength(3);
    expect(selected.map(({ topic_id }) => topic_id)).toEqual([
      "t05-small-molecule-representation",
      "t11-physical-model-system-state",
      "t15-experiment-pool-budget-feasibility",
    ]);
    expect(selected.map(({ implementation }) => implementation.status)).toEqual(
      ["completed", "completed", "completed"],
    );
    expect(JSON.stringify(record)).not.toMatch(
      /model_performance|test_result|observed_mae|observed_rmse/iu,
    );
  });

  it("preserves the frozen selection while validating live implementation state", async () => {
    const [systems, taxonomy, record] = await Promise.all([
      loadComparisonSystems(`${repositoryRoot}/catalog/comparisons/systems`, {
        today: latestCurrentCalendarDate(),
      }),
      loadComparisonTaxonomy(
        `${repositoryRoot}/catalog/comparisons/taxonomy.yaml`,
      ),
      loadDepthCandidateSet(
        `${repositoryRoot}/catalog/comparisons/depth-candidates.yaml`,
        { today: latestCurrentCalendarDate() },
      ),
    ]);
    const matrix = buildComparisonMatrix(systems, taxonomy);
    const gaps = buildGapTopics(matrix);

    expect(() =>
      validateDepthCandidatesAgainstAudit(record, gaps, taxonomy, matrix),
    ).not.toThrow();

    const altered = structuredClone(record);
    altered.candidates[0]!.prerequisite_value -= 1;
    expect(() =>
      validateDepthCandidatesAgainstAudit(altered, gaps, taxonomy, matrix),
    ).toThrow("prerequisite_value");

    const staleStatus = structuredClone(record);
    staleStatus.candidates[0]!.implementation.status = "planned";
    expect(() =>
      validateDepthCandidatesAgainstAudit(staleStatus, gaps, taxonomy, matrix),
    ).toThrow("implementation.status");

    const missingAssessment = structuredClone(matrix);
    const liveT11 = missingAssessment.find(
      ({ provider_id, topic_id }) =>
        provider_id === "aidd-commons" &&
        topic_id === "t11-physical-model-system-state",
    );
    expect(liveT11).toBeDefined();
    liveT11!.depth = "executable";
    expect(() =>
      validateDepthCandidatesAgainstAudit(
        record,
        buildGapTopics(missingAssessment),
        taxonomy,
        missingAssessment,
      ),
    ).toThrow("completed requires assessed current AIDD Commons evidence");
  });
});
