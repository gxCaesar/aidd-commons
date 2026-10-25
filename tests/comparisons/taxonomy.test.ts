import { describe, expect, it } from "vitest";

import { loadComparisonSystems } from "../../scripts/comparisons/comparisons.js";
import {
  loadComparisonTaxonomy,
  validateCoverageTopics,
} from "../../scripts/comparisons/taxonomy.js";
import { expectedTrackIds } from "../../scripts/curriculum/curriculum.js";

const fixtureRoot = "tests/comparisons/fixtures";

async function expectInvalid(
  fixture: string,
  expectedDiagnostic: string,
): Promise<void> {
  await expect(
    loadComparisonTaxonomy(`${fixtureRoot}/${fixture}`),
  ).rejects.toThrow(expectedDiagnostic);
}

describe("comparison taxonomy contract", () => {
  it("contains every charter track exactly once and in charter order", async () => {
    const taxonomy = await loadComparisonTaxonomy(
      "catalog/comparisons/taxonomy.yaml",
    );

    expect(taxonomy.tracks.map(({ id }) => id)).toEqual(expectedTrackIds);
  });

  it("requires all eighteen charter tracks", async () => {
    await expectInvalid(
      "bad-taxonomy-missing-track.yaml",
      "must define exactly 18 tracks",
    );
  });

  it("rejects a topic ID reused across tracks", async () => {
    await expectInvalid(
      "bad-taxonomy-duplicate-topic.yaml",
      "duplicates topic ID",
    );
  });

  it("rejects an unresolved topic prerequisite", async () => {
    await expectInvalid(
      "bad-taxonomy-unresolved-prerequisite.yaml",
      "does not resolve to a taxonomy topic ID",
    );
  });

  it("requires topic prerequisites to point backward", async () => {
    await expectInvalid(
      "bad-taxonomy-forward-prerequisite.yaml",
      "must point to an earlier topic",
    );
  });

  it("requires tracks to keep charter order", async () => {
    await expectInvalid(
      "bad-taxonomy-track-order.yaml",
      "tracks.0.order: must be sequential starting at 1",
    );
  });

  it("requires topics to keep sequential order within a track", async () => {
    await expectInvalid(
      "bad-taxonomy-topic-order.yaml",
      "topics.0.order: must be sequential within its track starting at 1",
    );
  });

  it("requires every track to contain a core topic", async () => {
    await expectInvalid(
      "bad-taxonomy-no-core.yaml",
      "must contain at least one core topic",
    );
  });

  it("rejects provider coverage for an unknown topic", async () => {
    const taxonomy = await loadComparisonTaxonomy(
      "catalog/comparisons/taxonomy.yaml",
    );
    const [system] = await loadComparisonSystems(
      `${fixtureRoot}/valid-minimal.yaml`,
      { today: "2026-09-04" },
    );
    const systemsWithUnknownTopic = [
      {
        ...system,
        coverage: system.coverage.map((observation, index) =>
          index === 0
            ? { ...observation, topic_id: "unknown-comparison-topic" }
            : observation,
        ),
      },
    ];

    expect(() =>
      validateCoverageTopics(systemsWithUnknownTopic, taxonomy),
    ).toThrow("does not resolve to a taxonomy topic");
  });

  it("rejects omitted provider-topic cells without an explicit default", async () => {
    const taxonomy = await loadComparisonTaxonomy(
      "catalog/comparisons/taxonomy.yaml",
    );
    const systems = await loadComparisonSystems(
      `${fixtureRoot}/valid-minimal.yaml`,
      { today: "2026-09-04" },
    );

    expect(() => validateCoverageTopics(systems, taxonomy)).toThrow(
      "coverage_default",
    );
  });
});
