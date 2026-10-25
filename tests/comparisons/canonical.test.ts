import { stat } from "node:fs/promises";

import { describe, expect, it } from "vitest";

import { loadComparisonSystems } from "../../scripts/comparisons/comparisons.js";
import { latestCurrentCalendarDate } from "../../catalog/schema/resource.js";
import {
  loadComparisonTaxonomy,
  validateCoverageTopics,
} from "../../scripts/comparisons/taxonomy.js";

const expectedSystemIds = [
  "agil",
  "aidd-commons",
  "build-ai-drug-discovery-pipelines",
  "chembl-training",
  "deepchem-tutorials",
  "european-aidd-network",
  "ml4drug-book",
  "o3dc",
  "openmm-cookbook",
  "practical-cheminformatics",
  "rdkit-cookbook",
  "teachopencadd",
  "therapeutics-data-commons",
];

describe("canonical comparison set", () => {
  it("freezes twelve external systems plus AIDD Commons", async () => {
    const systems = await loadComparisonSystems("catalog/comparisons/systems", {
      today: latestCurrentCalendarDate(),
    });
    const external = systems.filter(({ id }) => id !== "aidd-commons");

    expect(systems.map(({ id }) => id)).toEqual(expectedSystemIds);
    expect(external).toHaveLength(12);
    expect(
      new Set(external.map(({ provider_class }) => provider_class)),
    ).toEqual(
      new Set([
        "curriculum",
        "tutorial-collection",
        "benchmark-hub",
        "specialist-reference",
      ]),
    );
    expect(
      external.every(
        ({ canonical_url, canonical_repository_path }) =>
          canonical_url?.startsWith("https://") &&
          canonical_repository_path === undefined,
      ),
    ).toBe(true);
    const selfAudit = systems.find(({ id }) => id === "aidd-commons");
    expect(selfAudit).not.toHaveProperty("canonical_url");
    expect(selfAudit).toMatchObject({
      canonical_repository_path: "README.md",
    });
    expect(
      systems.every(
        ({ coverage_default }) =>
          coverage_default?.depth === "unverified" &&
          coverage_default.evidence.length === 0,
      ),
    ).toBe(true);
    expect(systems.every(({ coverage }) => coverage.length > 0)).toBe(true);
  });

  it("resolves every AIDD Commons repository source to a regular file", async () => {
    const systems = await loadComparisonSystems("catalog/comparisons/systems", {
      today: latestCurrentCalendarDate(),
    });
    const selfAudit = systems.find(({ id }) => id === "aidd-commons");
    expect(selfAudit).toBeDefined();

    const repositoryPaths = [
      selfAudit?.canonical_repository_path,
      ...(selfAudit?.evidence.map(({ repository_path }) => repository_path) ??
        []),
    ].filter((path): path is string => path !== undefined);
    const sourceStats = await Promise.all(
      repositoryPaths.map((path) => stat(path)),
    );

    expect(repositoryPaths.length).toBeGreaterThan(1);
    expect(sourceStats.every((source) => source.isFile())).toBe(true);
  });

  it("resolves every canonical coverage observation to the frozen taxonomy", async () => {
    const [systems, taxonomy] = await Promise.all([
      loadComparisonSystems("catalog/comparisons/systems", {
        today: latestCurrentCalendarDate(),
      }),
      loadComparisonTaxonomy("catalog/comparisons/taxonomy.yaml"),
    ]);

    expect(() => validateCoverageTopics(systems, taxonomy)).not.toThrow();
  });
});
