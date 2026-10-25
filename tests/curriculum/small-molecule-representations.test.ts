import { readFile } from "node:fs/promises";
import { join } from "node:path";
import { fileURLToPath } from "node:url";

import { describe, expect, it } from "vitest";
import { parse } from "yaml";

const repositoryRoot = fileURLToPath(new URL("../..", import.meta.url));
const lessonPath = join(
  repositoryRoot,
  "site/src/content/docs/learn/representations/small-molecule-representations.mdx",
);

describe("small-molecule representations depth lesson", () => {
  it("registers an ordered substantive lesson with resolved public sources", async () => {
    const curriculum = parse(
      await readFile(
        join(repositoryRoot, "catalog/curriculum/tracks.yaml"),
        "utf8",
      ),
    ) as {
      tracks: Array<{
        id: string;
        lessons: Array<{
          id: string;
          order: number;
          prerequisites: string[];
          sections: string[];
          source_ids: string[];
          type: string;
        }>;
      }>;
    };
    const track = curriculum.tracks.find(({ id }) => id === "representations");
    const lesson = track?.lessons.find(
      ({ id }) => id === "small-molecule-representations",
    );

    expect(lesson).toMatchObject({
      order: 2,
      prerequisites: ["biological-representations"],
      type: "lesson",
    });
    expect(lesson?.source_ids).toEqual(
      expect.arrayContaining(["tool-rdkit", "db-chembl"]),
    );
    expect(lesson?.sections).toEqual(
      expect.arrayContaining([
        "prerequisites",
        "goals",
        "scientific-assumptions",
        "data-contract",
        "representation-families",
        "cheap-baseline",
        "worked-case",
        "evaluation-traps",
        "failure-modes",
        "openness-and-licensing",
        "source-list",
      ]),
    );
  });

  it("publishes the chapter contract, decision matrix, runnable lab, and primary sources", async () => {
    const lesson = await readFile(lessonPath, "utf8");

    for (const heading of [
      "## Prerequisites",
      "## Learning goals",
      "## Scientific assumptions",
      "## Data contract",
      "## Representation families",
      "## Cheap baselines before learned encoders",
      "## Worked case: one structure, several computational objects",
      "## Evaluation traps",
      "## Failure modes and cheapest checks",
      "## Openness and licensing",
      "## Sources and further study",
    ]) {
      expect(lesson).toContain(heading);
    }

    for (const concept of [
      "SMILES",
      "InChI",
      "SELFIES",
      "descriptors",
      "Morgan",
      "molecular graph",
      "conformer",
      "stereochemistry",
      "tautomer",
      "protonation",
      "applicability domain",
    ]) {
      expect(lesson).toMatch(new RegExp(concept, "iu"));
    }

    for (const source of [
      "https://github.com/opensmiles/OpenSMILES/blob/master/opensmiles.asciidoc",
      "https://iupac.org/who-we-are/divisions/division-details/inchi/",
      "https://www.rdkit.org/docs/RDKit_Book.html",
      "https://doi.org/10.1021/ci100050t",
      "https://proceedings.mlr.press/v70/gilmer17a.html",
      "https://papers.nips.cc/paper/2017/hash/303ed4c69846ab36c2904d3ba8573050-Abstract.html",
      "https://doi.org/10.1039/C7SC02664A",
    ]) {
      expect(lesson).toContain(source);
    }

    expect(lesson).toContain("/labs/molecule-representation-inspector/");
    expect(lesson).toMatch(/label-free\s+identity inspector/u);
    expect(lesson).toContain("/labs/chembl-egfr-representation-baselines/");
    expect(lesson).toContain(
      "/labs/chembl-egfr-representation-baselines/#chembl-locked-title",
    );
    expect(lesson).toContain("Last reviewed: 2026-09-08");
  });

  it("keeps the broad introduction and Chinese pathway connected to the deep lesson", async () => {
    const [introduction, chinesePathway] = await Promise.all([
      readFile(
        join(
          repositoryRoot,
          "site/src/content/docs/learn/representations/biological-representations.mdx",
        ),
        "utf8",
      ),
      readFile(
        join(
          repositoryRoot,
          "site/src/content/docs/zh-cn/pathways/representations.mdx",
        ),
        "utf8",
      ),
    ]);
    const route = "/learn/representations/small-molecule-representations/";

    expect(introduction).toContain(route);
    expect(chinesePathway).toContain(route);
    expect(chinesePathway).toContain(
      "/labs/molecule-representation-inspector/",
    );
  });

  it("publishes a label-free lab page and exposes it from the Labs index", async () => {
    const [lab, labIndex] = await Promise.all([
      readFile(
        join(
          repositoryRoot,
          "site/src/content/docs/labs/molecule-representation-inspector.mdx",
        ),
        "utf8",
      ),
      readFile(join(repositoryRoot, "site/src/pages/labs/index.astro"), "utf8"),
    ]);

    expect(lab).toContain(
      "title: Label-free molecule representation inspector",
    );
    expect(lab).toContain("## Input and output contract");
    expect(lab).toContain("## Expected relationships");
    expect(lab).toContain("does not load activity labels");
    expect(lab).toContain("Last reviewed: 2026-09-08");
    expect(labIndex).toContain(
      'href="/labs/molecule-representation-inspector/"',
    );
    expect(labIndex).toContain("Executable representation lab");
  });

  it("promotes the delivered T05 surfaces in the dated self-audit", async () => {
    const selfAudit = parse(
      await readFile(
        join(repositoryRoot, "catalog/comparisons/systems/aidd-commons.yaml"),
        "utf8",
      ),
    ) as {
      coverage: Array<{
        depth: string;
        evidence: string[];
        topic_id: string;
      }>;
      evidence: Array<{ id: string; repository_path?: string }>;
      last_verified: string;
    };
    const observation = selfAudit.coverage.find(
      ({ topic_id }) => topic_id === "t05-small-molecule-representation",
    );

    expect(observation).toMatchObject({ depth: "assessed" });
    expect(observation?.evidence).toEqual([
      "representations-depth-lesson",
      "representations-inspector-page",
      "representations-inspector-readme",
      "representations-inspector-cli",
      "representations-inspector-engine",
      "chembl-egfr-lab-page",
      "chembl-egfr-protocol",
      "chembl-egfr-development-summary",
      "chembl-egfr-cli",
      "chembl-egfr-engine",
      "chembl-egfr-locked-summary",
    ]);
    expect(
      selfAudit.evidence
        .filter(({ id }) => observation?.evidence.includes(id))
        .map(({ repository_path }) => repository_path),
    ).toEqual([
      "site/src/content/docs/learn/representations/small-molecule-representations.mdx",
      "site/src/content/docs/labs/molecule-representation-inspector.mdx",
      "labs/molecule_representations/README.md",
      "labs/molecule_representations/run_lab.py",
      "labs/src/aidd_commons/representations/inspection.py",
      "site/src/content/docs/labs/chembl-egfr-representation-baselines.mdx",
      "labs/chembl_egfr/protocol.json",
      "labs/chembl_egfr/development-summary.json",
      "labs/chembl_egfr/run_lab.py",
      "labs/src/aidd_commons/chembl_egfr/pipeline.py",
      "labs/chembl_egfr/locked-summary.json",
    ]);
    // The record date moves whenever any topic gains evidence, most recently
    // the cross-domain trade-off topic on 2026-10-24. The T05 evidence set
    // above is unchanged by those passes, which is what this test actually
    // guards.
    expect(selfAudit.last_verified).toBe("2026-10-24");
  });
});
