import { readFile } from "node:fs/promises";
import { join } from "node:path";
import { fileURLToPath } from "node:url";

import { describe, expect, it } from "vitest";
import { parse } from "yaml";

const repositoryRoot = fileURLToPath(new URL("../..", import.meta.url));
const lessonRoute =
  "/learn/physics-based-modeling/physical-model-system-state/";
const labRoute = "/labs/rmd17-system-state-energy-baselines/";
const rmd17Doi = "10.6084/m9.figshare.12672038.v4";
const primaryPaperDoi = "10.1088/2632-2153/abba6f";
const incorrectOrbnetDoi = "10.1063/5.0021955";

describe("rMD17 physical-model system-state curriculum tranche", () => {
  it("orders the substantive lesson between the introduction and core-source path", async () => {
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
    const track = curriculum.tracks.find(
      ({ id }) => id === "physics-based-modeling",
    );
    const depthLesson = track?.lessons.find(
      ({ id }) => id === "physical-model-system-state",
    );
    const coreSourcePath = track?.lessons.find(
      ({ id }) => id === "physics-core-source-path",
    );

    const introduction = track?.lessons.find(
      ({ id }) => id === "docking-to-fep",
    );
    expect(introduction).toBeDefined();
    expect(depthLesson).toBeDefined();
    expect(coreSourcePath).toBeDefined();
    expect(introduction!.order).toBeLessThan(depthLesson!.order);
    expect(depthLesson!.order).toBeLessThan(coreSourcePath!.order);
    expect(depthLesson).toMatchObject({
      prerequisites: ["docking-to-fep"],
      type: "lesson",
    });
    expect(depthLesson?.source_ids).toEqual([
      "dataset-rmd17",
      "tool-mdanalysis",
      "tool-openmm",
    ]);
    expect(depthLesson?.sections).toEqual([
      "prerequisites",
      "goals",
      "state-anatomy",
      "data-contract",
      "ordering-and-dependence",
      "invariant-representation",
      "train-only-fitting",
      "system-level-evaluation",
      "worked-lab",
      "failure-gates",
      "limitations",
      "source-list",
    ]);
    expect(coreSourcePath).toMatchObject({
      prerequisites: ["physical-model-system-state"],
      type: "core-source-path",
    });
  });

  it("records the versioned rMD17 source, dataset-only CC0 scope, and unresolved openness fields", async () => {
    const resource = parse(
      await readFile(
        join(repositoryRoot, "catalog/resources/dataset-rmd17.yaml"),
        "utf8",
      ),
    ) as {
      canonical_url: string;
      id: string;
      identifiers: Array<{ scheme: string; value: string }>;
      kind: string;
      licenses: Array<{ evidence: string[]; name: string; scope: string }>;
      openness: Record<string, { value: string }>;
    };

    expect(resource).toMatchObject({
      id: "dataset-rmd17",
      kind: "dataset",
      canonical_url: `https://doi.org/${rmd17Doi}`,
    });
    expect(resource.identifiers).toEqual(
      expect.arrayContaining([
        expect.objectContaining({ scheme: "figshare-doi", value: rmd17Doi }),
        expect.objectContaining({
          scheme: "primary-paper-doi",
          value: primaryPaperDoi,
        }),
      ]),
    );
    expect(resource.licenses).toEqual([
      {
        name: "CC0",
        scope:
          "rMD17 Figshare version-4 dataset files and record metadata only; not lesson prose, software, models, or other assets.",
        evidence: ["figshare-v4-record"],
      },
    ]);
    expect(
      Object.values(resource.openness).every(
        ({ value }) => value === "unverified",
      ),
    ).toBe(true);
    expect(JSON.stringify(resource)).not.toContain(incorrectOrbnetDoi);
  });

  it("teaches the data, model, nested-unit, and locked-evaluation boundaries without duplicating panel metrics", async () => {
    const [lesson, labPage, labReadme, introduction, chinesePathway] =
      await Promise.all([
        readFile(
          join(
            repositoryRoot,
            "site/src/content/docs/learn/physics-based-modeling/physical-model-system-state.mdx",
          ),
          "utf8",
        ),
        readFile(
          join(
            repositoryRoot,
            "site/src/content/docs/labs/rmd17-system-state-energy-baselines.mdx",
          ),
          "utf8",
        ),
        readFile(
          join(repositoryRoot, "labs/rmd17_system_state/README.md"),
          "utf8",
        ),
        readFile(
          join(
            repositoryRoot,
            "site/src/content/docs/learn/physics-based-modeling/docking-to-fep.mdx",
          ),
          "utf8",
        ),
        readFile(
          join(
            repositoryRoot,
            "site/src/content/docs/zh-cn/pathways/physics-based-modeling.mdx",
          ),
          "utf8",
        ),
      ]);

    expect(lesson).toContain(
      'import Rmd17DevelopmentPanel from "../../../../components/Rmd17DevelopmentPanel.astro";',
    );
    expect(lesson).toContain("<Rmd17DevelopmentPanel />");
    for (const heading of [
      "## Prerequisites",
      "## Learning goals",
      "## State anatomy and observed variables",
      "## NPZ data and unit contract",
      "## Original-index ordering and nested dependence",
      "## Invariant representation and its limits",
      "## Train-only fitting and shared alpha selection",
      "## System-level evaluation and the development boundary",
      "## Worked lab route and commands",
      "## Exercises",
      "## Failure gates and limitations",
      "## Sources and attribution",
    ]) {
      expect(lesson).toContain(heading);
    }
    for (const term of [
      rmd17Doi,
      primaryPaperDoi,
      "100,000",
      "600/200/200",
      "stable ascending sort",
      "time-correlated",
      "molecular system",
      "100 bins",
      "overflow",
      "translation",
      "rotation",
      "same-element permutation",
      "StandardScaler",
      "exact ties choose larger alpha",
      "n=2",
      "procedural",
      "energy-only",
      "five source-provided train/test CSV pairs are not used",
      "does not identify those CSV indices as a temporal order",
    ]) {
      expect(lesson).toContain(term);
    }
    for (const command of [
      "validate-protocol",
      "download-development",
      "pretest",
    ]) {
      expect(lesson).toContain(command);
    }
    expect(lesson).toContain(labRoute);
    expect(lesson).not.toContain(incorrectOrbnetDoi);
    expect(lesson).not.toContain("2.4810026728771484");
    expect(lesson).not.toContain("2.74979407419567");
    expect(introduction).toContain(lessonRoute);
    expect(introduction).toContain(labRoute);
    expect(introduction).not.toContain("Its expected [rMD17");
    expect(chinesePathway).toContain(lessonRoute);
    expect(chinesePathway).toContain(labRoute);
    expect(chinesePathway).not.toContain("预定的");
    expect(lesson).not.toContain("The expected [rMD17");
    expect(labReadme).toContain("original-index ordering challenge");
    expect(labReadme).toContain(
      "source-provided train/test CSV pairs are not used",
    );
    expect(labReadme).not.toContain("chronological challenge");
    for (const publicLabSurface of [labPage, labReadme]) {
      expect(publicLabSurface).not.toContain("evaluate-locked");
      expect(publicLabSurface).not.toContain("--confirm-run-locked-evaluation");
      expect(publicLabSurface).not.toContain("exclusive marker");
    }
  });

  it("records completed assessed T11 delivery while preserving the selection-time record", async () => {
    const [candidateSet, selfAudit, roadmap] = await Promise.all([
      readFile(
        join(repositoryRoot, "catalog/comparisons/depth-candidates.yaml"),
        "utf8",
      ),
      readFile(
        join(repositoryRoot, "catalog/comparisons/systems/aidd-commons.yaml"),
        "utf8",
      ),
      readFile(join(repositoryRoot, "docs/ROADMAP_V0.2.md"), "utf8"),
    ]);
    const candidates = parse(candidateSet) as {
      candidates: Array<{
        cheap_baseline: { protocol: string };
        data_feasibility: { source_url: string };
        evidence: Array<{ id: string; url: string }>;
        implementation: { note: string; status: string };
        independent_unit: { note: string; observed_units: number };
        topic_id: string;
      }>;
    };
    const selfAuditRecord = parse(selfAudit) as {
      coverage: Array<{ depth: string; evidence: string[]; topic_id: string }>;
      evidence: Array<{ id: string; repository_path?: string }>;
    };
    const candidate = candidates.candidates.find(
      ({ topic_id }) => topic_id === "t11-physical-model-system-state",
    );
    const coverage = selfAuditRecord.coverage.find(
      ({ topic_id }) => topic_id === "t11-physical-model-system-state",
    );

    expect(candidate?.implementation.status).toBe("completed");
    expect(candidate?.data_feasibility.source_url).toBe(
      `https://doi.org/${rmd17Doi}`,
    );
    expect(candidate?.cheap_baseline.protocol).toContain("train-only");
    expect(candidate?.cheap_baseline.protocol).toContain(
      "exact ties choose larger alpha",
    );
    expect(candidate?.independent_unit.observed_units).toBe(2);
    expect(candidate?.independent_unit.note).toContain(
      "Two molecular systems have observed development evaluation",
    );
    expect(candidate?.independent_unit.note).toContain(
      "benzene and uracil remain not_run",
    );
    expect(candidate?.evidence.map(({ url }) => url)).toEqual(
      expect.arrayContaining([
        `https://doi.org/${rmd17Doi}`,
        `https://doi.org/${primaryPaperDoi}`,
      ]),
    );
    expect(JSON.stringify(candidate)).not.toContain(incorrectOrbnetDoi);

    const expectedEvidence = [
      "rmd17-depth-lesson",
      "rmd17-lab-page",
      "rmd17-protocol",
      "rmd17-development-summary",
      "rmd17-cli",
      "rmd17-engine",
      "rmd17-locked-summary",
    ];
    expect(coverage).toMatchObject({ depth: "assessed" });
    expect(coverage?.evidence).toEqual(expectedEvidence);
    expect(
      selfAuditRecord.evidence
        .filter(({ id }) => coverage?.evidence.includes(id))
        .map(({ repository_path }) => repository_path),
    ).toEqual([
      "site/src/content/docs/learn/physics-based-modeling/physical-model-system-state.mdx",
      "site/src/content/docs/labs/rmd17-system-state-energy-baselines.mdx",
      "labs/rmd17_system_state/protocol.json",
      "labs/rmd17_system_state/development-summary.json",
      "labs/rmd17_system_state/run_lab.py",
      "labs/src/aidd_commons/rmd17_system_state/pipeline.py",
      "labs/rmd17_system_state/locked-summary.json",
    ]);

    expect(roadmap).toContain(
      "`t11-physical-model-system-state` is `completed`",
    );
    expect(roadmap).toContain("n=2 development systems");
    expect(roadmap).toContain("2.4810026728771484");
    expect(roadmap).toContain("2.74979407419567");
  });
});
