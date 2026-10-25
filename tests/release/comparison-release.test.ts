import { access, mkdtemp, readFile, rm } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { fileURLToPath } from "node:url";

import { afterAll, describe, expect, it } from "vitest";

const repositoryRoot = fileURLToPath(new URL("../..", import.meta.url));

async function expectFile(path: string) {
  await expect(access(path)).resolves.toBeUndefined();
}

describe("comparison audit public release", () => {
  let workspace: string | undefined;

  afterAll(async () => {
    if (workspace !== undefined) {
      await rm(workspace, { recursive: true, force: true });
    }
  });

  it("publishes the complete public audit surface and excludes internal plans", async () => {
    const { buildPublicRelease } = await import(
      "../../scripts/release/build.js"
    );
    workspace = await mkdtemp(join(tmpdir(), "aidd-comparison-release-"));
    const destination = join(workspace, "public-release");
    const inventoryPath = join(workspace, "inventory.txt");

    const result = await buildPublicRelease({
      destination,
      inventoryPath,
      sourceRoot: repositoryRoot,
    });

    for (const relativePath of [
      "catalog/comparisons/depth-candidates.yaml",
      "catalog/comparisons/taxonomy.yaml",
      "catalog/comparisons/systems/aidd-commons.yaml",
      "catalog/schema/comparison.ts",
      "catalog/schema/comparison-taxonomy.ts",
      "catalog/schema/depth-candidate.ts",
      "docs/COMPARISON_AUDIT.md",
      "docs/COMPARISON_SEARCH_LEDGER.md",
      "scripts/comparisons/export.ts",
      "scripts/comparisons/depth-candidates.ts",
      "scripts/comparisons/validate.ts",
      "site/public/data/comparison.v1.csv",
      "site/public/data/comparison.v1.json",
      "site/src/components/ComparisonMatrix.astro",
      "site/src/components/CoverageBounds.astro",
      "site/src/pages/audit/index.astro",
      "tests/comparisons/schema.test.ts",
      "tests/comparisons/depth-candidates.test.ts",
      "tests/site/comparison-audit.test.ts",
      "labs/pool_budget/README.md",
      "labs/pool_budget/protocol.json",
      "labs/pool_budget/real-protocol.json",
      "labs/pool_budget/REAL_PROTOCOL.md",
      "labs/chembl_egfr/execution-amendment.json",
      "labs/pool_budget/run_lab.py",
      "labs/pool_budget/run_real_campaign.py",
      "labs/pool_budget/demo-summary.json",
      "labs/pool_budget/real-summary.json",
      "labs/pool_budget/export_summary.py",
      "labs/src/aidd_commons/pool_budget.py",
      "site/src/components/PoolBudgetPanel.astro",
      "site/src/components/PoolBudgetRealPanel.astro",
      "labs/chembl_egfr/locked-summary.json",
      "labs/chembl_egfr/export_locked_summary.py",
      "labs/rmd17_system_state/locked-summary.json",
      "labs/rmd17_system_state/export_locked_summary.py",
      "site/src/components/ChemblLockedPanel.astro",
      "site/src/components/Rmd17LockedPanel.astro",
    ]) {
      await expectFile(join(destination, relativePath));
    }

    await expect(access(join(destination, ".superpowers"))).rejects.toThrow();
    await expect(
      access(join(destination, "labs/pool_budget/results")),
    ).rejects.toThrow();
    for (const lab of ["chembl_egfr", "rmd17_system_state"]) {
      await expect(
        access(join(destination, "labs", lab, "results")),
      ).rejects.toThrow();
      await expect(
        access(join(destination, "labs", lab, "data")),
      ).rejects.toThrow();
    }
    await expect(
      readFile(join(destination, "public-release.inventory.txt"), "utf8"),
    ).rejects.toThrow();
    expect(result.findings).toEqual([]);
    await expect(readFile(inventoryPath, "utf8")).resolves.toContain(
      "catalog/comparisons/taxonomy.yaml",
    );
  }, 30_000);
});
