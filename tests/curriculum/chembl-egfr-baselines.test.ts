import { readFile } from "node:fs/promises";
import { join } from "node:path";
import { fileURLToPath } from "node:url";

import { parse } from "yaml";
import { describe, expect, it } from "vitest";

const repositoryRoot = fileURLToPath(new URL("../..", import.meta.url));

describe("ChEMBL 37 EGFR representation baseline tranche", () => {
  it("publishes the exact frozen protocol and reviewed development-only evidence", async () => {
    const protocol = JSON.parse(
      await readFile(
        join(repositoryRoot, "labs/chembl_egfr/protocol.json"),
        "utf8",
      ),
    );
    const summary = JSON.parse(
      await readFile(
        join(repositoryRoot, "labs/chembl_egfr/development-summary.json"),
        "utf8",
      ),
    );

    expect(protocol.protocol_version).toBe("chembl37-egfr-representation-v1");
    expect(
      protocol.representations.descriptor_ridge.descriptor_names,
    ).toHaveLength(214);
    expect(protocol.representations.morgan_ridge).toMatchObject({
      bits: 2048,
      form: "binary ExplicitBitVect",
      include_chirality: true,
      radius: 2,
    });
    expect(protocol.models.ridge_alphas).toEqual([
      0.001, 0.01, 0.1, 1, 10, 100, 1000,
    ]);
    expect(protocol.labels.pchembl_consistency_tolerance).toBe(0.011);
    expect(protocol.locked_evaluation.state).toBe("not_run");

    expect(summary.data.primary).toMatchObject({
      duplicate_parent_count: 57,
      input_rows: 975,
      parent_count: 902,
      retained_rows: 966,
    });
    expect(summary.data.replication).toMatchObject({
      input_rows: 173,
      parent_count: 170,
      retained_rows: 173,
    });
    expect(summary.data.parent_overlap).toBe(0);
    expect(summary.split).toMatchObject({
      actual_counts: { test: 132, train: 634, validation: 136 },
      scaffold_counts: { primary: 238, replication: 23 },
    });
    expect(summary.selection.selected_alphas).toEqual({
      descriptor_ridge: 1000,
      morgan_ridge: 1,
    });
    expect(summary.locked_evaluations).toEqual({
      primary: "not_run",
      replication: "not_run",
    });
  });

  it("renders the evidence panel from the reviewed aggregate summary", async () => {
    const component = await readFile(
      join(repositoryRoot, "site/src/components/ChemblPretestPanel.astro"),
      "utf8",
    );

    expect(component).toContain("development-summary.json");
    expect(component).not.toContain('mae: "0.373"');
    expect(component).not.toContain('["975", "queried rows"]');
  });

  it("teaches the data funnel, frozen comparison, boundary result, and lock", async () => {
    const [page, readme, labIndex, lesson, summaryText] = await Promise.all([
      readFile(
        join(
          repositoryRoot,
          "site/src/content/docs/labs/chembl-egfr-representation-baselines.mdx",
        ),
        "utf8",
      ),
      readFile(join(repositoryRoot, "labs/chembl_egfr/README.md"), "utf8"),
      readFile(join(repositoryRoot, "site/src/pages/labs/index.astro"), "utf8"),
      readFile(
        join(
          repositoryRoot,
          "site/src/content/docs/learn/representations/small-molecule-representations.mdx",
        ),
        "utf8",
      ),
      readFile(
        join(repositoryRoot, "labs/chembl_egfr/development-summary.json"),
        "utf8",
      ),
    ]);
    const summary = JSON.parse(summaryText) as {
      data: {
        primary: {
          input_rows: number;
          parent_count: number;
          retained_rows: number;
        };
        replication: { input_rows: number; parent_count: number };
      };
      selection: {
        metrics: Record<string, { mae: number; rmse: number }>;
        selected_alphas: Record<string, number>;
      };
      split: { actual_counts: Record<string, number> };
    };

    for (const heading of [
      "## Learning objectives",
      "## Source and endpoint contract",
      "## Entity and label contract",
      "## Frozen representations",
      "## Scaffold split",
      "## Development-only observations",
      "## Run the lab",
      "## Completed evaluation and remaining boundaries",
      "## Exercises",
      "## Limitations and failure gates",
      "## Sources and attribution",
    ]) {
      expect(page).toContain(heading);
    }
    expect(page).toMatch(/descriptor alpha lies\s+at the upper edge/u);
    for (const value of [
      summary.data.primary.input_rows,
      summary.data.primary.retained_rows,
      summary.data.primary.parent_count,
      summary.data.replication.input_rows,
      summary.data.replication.parent_count,
      ...Object.values(summary.split.actual_counts),
      ...Object.values(summary.selection.selected_alphas),
    ]) {
      expect(page).toContain(String(value));
    }
    for (const metrics of Object.values(summary.selection.metrics)) {
      expect(page).toContain(metrics.mae.toFixed(6));
      expect(page).toContain(metrics.rmse.toFixed(6));
    }
    expect(page).toContain("procedural lock");
    expect(page).toContain("public ChEMBL labels are secret");
    expect(readme).toContain("evaluate-locked");
    for (const document of [page, readme]) {
      expect(document).toContain("time-bounded");
      expect(document).toContain("chembl_37_sqlite.tar.gz");
      expect(document).toMatch(/does not (?:yet )?automate/u);
      expect(document).toContain("0.011 pChEMBL tolerance");
    }
    expect(labIndex).toContain(
      'href="/labs/chembl-egfr-representation-baselines/"',
    );
    expect(lesson).toContain("/labs/chembl-egfr-representation-baselines/");
    expect(lesson).toContain("214 frozen RDKit 2D descriptors");
  });

  it("records completed delivery with separate development and evaluation evidence", async () => {
    const candidates = parse(
      await readFile(
        join(repositoryRoot, "catalog/comparisons/depth-candidates.yaml"),
        "utf8",
      ),
    ) as {
      candidates: Array<{
        implementation: { note: string; status: string };
        independent_unit: { name: string };
        topic_id: string;
      }>;
    };
    const selfAudit = parse(
      await readFile(
        join(repositoryRoot, "catalog/comparisons/systems/aidd-commons.yaml"),
        "utf8",
      ),
    ) as {
      coverage: Array<{ evidence: string[]; topic_id: string }>;
      evidence: Array<{ id: string; repository_path?: string }>;
    };
    const candidate = candidates.candidates.find(
      ({ topic_id }) => topic_id === "t05-small-molecule-representation",
    );
    const coverage = selfAudit.coverage.find(
      ({ topic_id }) => topic_id === "t05-small-molecule-representation",
    );

    expect(candidate?.implementation.status).toBe("completed");
    expect(candidate?.independent_unit.name).toContain("chirality-aware");
    expect(coverage?.evidence).toEqual(
      expect.arrayContaining([
        "chembl-egfr-lab-page",
        "chembl-egfr-protocol",
        "chembl-egfr-development-summary",
        "chembl-egfr-cli",
        "chembl-egfr-engine",
        "chembl-egfr-locked-summary",
      ]),
    );
    expect(
      selfAudit.evidence
        .filter(({ id }) => coverage?.evidence.includes(id))
        .map(({ repository_path }) => repository_path),
    ).toEqual(
      expect.arrayContaining([
        "site/src/content/docs/labs/chembl-egfr-representation-baselines.mdx",
        "labs/chembl_egfr/protocol.json",
        "labs/chembl_egfr/development-summary.json",
        "labs/chembl_egfr/run_lab.py",
        "labs/src/aidd_commons/chembl_egfr/pipeline.py",
      ]),
    );
  });
});
