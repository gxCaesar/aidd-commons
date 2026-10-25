import { mkdtemp, readFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";

import { describe, expect, it } from "vitest";

import { buildCoverage } from "../../scripts/curriculum/coverage.js";

describe("catalog-derived curriculum coverage", () => {
  it("counts resources by track, kind, stage, access, and evidence state", async () => {
    const outputDirectory = await mkdtemp(join(tmpdir(), "aidd-coverage-"));
    const output = join(outputDirectory, "COVERAGE.md");
    const coverage = await buildCoverage({
      catalog: "catalog/resources",
      curriculum: "catalog/curriculum/tracks.yaml",
      output,
    });

    expect(coverage.resourceCount).toBeGreaterThanOrEqual(100);
    expect(Object.keys(coverage.byTrack)).toHaveLength(18);
    expect(Object.keys(coverage.byKind).length).toBeGreaterThan(1);
    expect(Object.keys(coverage.byStage).length).toBeGreaterThan(1);
    expect(Object.keys(coverage.byAccess)).toContain("unverified");
    expect(Object.keys(coverage.byEvidence)).toContain("metadata-supported");

    const report = await readFile(output, "utf8");
    expect(report).toContain("## Coverage by curriculum track");
    expect(report).toContain("| Category                       | Records |");
    expect(report).toContain("## Evidence-state interpretation");
    expect(report).toContain("## v0.2a measured comparison audit");
    expect(report).toMatch(/13 validated\s+learning systems/u);
    expect(report).toContain("t05-small-molecule-representation");
    expect(report).toContain("Small-molecule representations (completed)");
    expect(report).toContain("in the frozen selection snapshot");
    expect(report).toContain("not proof of comprehensiveness");
  });
});
