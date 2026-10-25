import { describe, expect, it } from "vitest";

import { loadComparisonSystems } from "../../scripts/comparisons/comparisons.js";

const fixtureRoot = "tests/comparisons/fixtures";

async function expectInvalid(
  fixture: string,
  expectedDiagnostic: string,
): Promise<void> {
  await expect(
    loadComparisonSystems(`${fixtureRoot}/${fixture}`, {
      today: "2026-09-04",
    }),
  ).rejects.toThrow(expectedDiagnostic);
}

describe("comparison system evidence contract", () => {
  it("accepts opened evidence from a repository-relative public path", async () => {
    const systems = await loadComparisonSystems(
      `${fixtureRoot}/valid-repository-evidence.yaml`,
      { today: "2026-09-04" },
    );

    expect(systems).toHaveLength(1);
    expect(systems[0]?.coverage_default).toMatchObject({
      depth: "unverified",
      evidence: [],
    });
  });

  it("rejects an absolute local path as public evidence", async () => {
    await expectInvalid(
      "bad-absolute-repository-evidence.yaml",
      "repository_path",
    );
  });

  it("rejects a hidden or internal repository path as public evidence", async () => {
    await expectInvalid(
      "bad-private-repository-evidence.yaml",
      "repository_path",
    );
  });

  it("rejects a repository evidence path that is not a regular source file", async () => {
    await expectInvalid(
      "bad-missing-repository-evidence.yaml",
      "does not resolve to a regular repository file",
    );
  });

  it("allows only unverified as an omitted-topic default", async () => {
    await expectInvalid(
      "bad-absent-coverage-default.yaml",
      "coverage_default.depth",
    );
  });

  it("returns directory records in stable ID order", async () => {
    const systems = await loadComparisonSystems(
      `${fixtureRoot}/ordered-systems`,
      { today: "2026-09-04" },
    );

    expect(systems.map(({ id }) => id)).toEqual([
      "alpha-system",
      "zeta-system",
    ]);
  });

  it("rejects a positive depth claim without evidence", async () => {
    await expectInvalid(
      "bad-positive-without-evidence.yaml",
      "coverage.0.evidence",
    );
  });

  it("requires a runnable cell to say whether real data carries it", async () => {
    await expectInvalid(
      "bad-runnable-without-run-basis.yaml",
      "coverage.0.run_basis",
    );
  });

  it("rejects a run basis on a depth with nothing runnable", async () => {
    await expectInvalid(
      "bad-run-basis-without-runnable-depth.yaml",
      "run_basis applies only to executable or assessed depth",
    );
  });

  it("rejects positive depth backed only by inaccessible evidence", async () => {
    await expectInvalid(
      "bad-positive-inaccessible-evidence.yaml",
      "must reference opened evidence",
    );
  });

  it("requires an absent observation to name a reviewed scope", async () => {
    await expectInvalid("bad-absent-without-scope.yaml", "reviewed_scope");
  });

  it("rejects evidence references that do not resolve in the record", async () => {
    await expectInvalid("bad-unresolved-evidence.yaml", "metadata_evidence.0");
  });

  it("rejects a review date later than the validator date", async () => {
    await expectInvalid("bad-future-review.yaml", "last_verified");
  });

  it("requires evidence for a non-unverified access claim", async () => {
    await expectInvalid(
      "bad-access-without-evidence.yaml",
      "access.content.evidence",
    );
  });

  it("rejects a licence supported only by inaccessible evidence", async () => {
    await expectInvalid(
      "bad-license-inaccessible-evidence.yaml",
      "licenses.0.evidence.0",
    );
  });

  it("requires evidence when a correction route is published", async () => {
    await expectInvalid(
      "bad-correction-without-evidence.yaml",
      "correction_evidence",
    );
  });

  it("requires displayed metadata to use opened evidence", async () => {
    await expectInvalid(
      "bad-metadata-inaccessible-evidence.yaml",
      "metadata_evidence.0",
    );
  });

  it("rejects duplicate evidence IDs within one system", async () => {
    await expectInvalid("bad-duplicate-evidence.yaml", "evidence.1.id");
  });

  it("rejects duplicate topic observations within one system", async () => {
    await expectInvalid("bad-duplicate-topic.yaml", "coverage.1.topic_id");
  });

  it("rejects evidence reviewed after the containing record", async () => {
    await expectInvalid(
      "bad-evidence-after-record-review.yaml",
      "evidence.0.reviewed_on",
    );
  });

  it("rejects duplicate system IDs across files", async () => {
    await expectInvalid("duplicate-systems", "duplicates comparison system id");
  });
});
