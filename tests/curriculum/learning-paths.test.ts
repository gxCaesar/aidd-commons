import { mkdtemp, readFile, rm, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { fileURLToPath } from "node:url";

import { describe, expect, it } from "vitest";
import { parse, stringify } from "yaml";

import { loadCatalog } from "../../scripts/catalog/catalog.js";
import { latestCurrentCalendarDate } from "../../catalog/schema/resource.js";
import {
  CurriculumValidationError,
  loadCurriculum,
} from "../../scripts/curriculum/curriculum.js";

const repositoryRoot = fileURLToPath(new URL("../..", import.meta.url));
const curriculumPath = join(
  repositoryRoot,
  "catalog",
  "curriculum",
  "tracks.yaml",
);
const siteBuildDirectory = join(repositoryRoot, "site", "dist");

type CurriculumSource = {
  learning_paths?: Array<{
    id: string;
    kind: "core" | "specialist";
    lesson_ids: string[];
    prerequisites: string[];
  }>;
  tracks: Array<{
    id: string;
    lessons: Array<{
      id: string;
      type?: string;
      [key: string]: unknown;
    }>;
  }>;
  units?: Array<{
    historical_topic_ids: string[];
    id: string;
    prerequisites: string[];
  }>;
};

async function sourceCurriculum(): Promise<CurriculumSource> {
  return parse(await readFile(curriculumPath, "utf8")) as CurriculumSource;
}

async function withCurriculum<T>(
  source: CurriculumSource,
  run: (path: string) => Promise<T>,
): Promise<T> {
  const directory = await mkdtemp(join(tmpdir(), "aidd-curriculum-"));
  const path = join(directory, "tracks.yaml");

  try {
    await writeFile(path, stringify(source));
    return await run(path);
  } finally {
    await rm(directory, { force: true, recursive: true });
  }
}

async function expectInvalid(source: CurriculumSource): Promise<string> {
  const resources = await loadCatalog("catalog/resources", {
    today: latestCurrentCalendarDate(),
  });

  return withCurriculum(source, async (path) => {
    try {
      await loadCurriculum(path, { resources });
    } catch (error) {
      expect(error).toBeInstanceOf(CurriculumValidationError);
      return (error as CurriculumValidationError).message;
    }
    throw new Error("Expected curriculum validation to fail");
  });
}

describe("explicit learning paths and curriculum units", () => {
  it("keeps the six ordered routes explicit when an unrelated advanced lesson is added", async () => {
    const baseline = await sourceCurriculum();
    const baselinePaths = baseline.learning_paths;

    expect(baselinePaths).toHaveLength(6);
    expect(baselinePaths?.map((path) => path.id)).toEqual([
      "core",
      "small-molecules",
      "structure-physics",
      "biologics",
      "targets-cells",
      "agents-feedback",
    ]);

    const extended = structuredClone(baseline);
    const candidateTrack = extended.tracks.find(
      (track) => track.id === "candidate-nomination",
    );
    if (!candidateTrack)
      throw new Error("candidate-nomination track is required");
    candidateTrack.lessons.push({
      id: "advanced-stability-check",
      order: candidateTrack.lessons.length + 1,
      title: "Advanced stability check",
      type: "lesson",
      sections: ["goals"],
      source_ids: ["tool-deepchem"],
      prerequisites: ["capstone"],
    });

    const resources = await loadCatalog("catalog/resources", {
      today: latestCurrentCalendarDate(),
    });
    const validated = await withCurriculum(extended, (path) =>
      loadCurriculum(path, { resources }),
    );

    expect(validated.learning_paths.map((path) => path.lesson_ids)).toEqual(
      baselinePaths?.map((path) => path.lesson_ids),
    );
    expect(
      validated.learning_paths.flatMap((path) => path.lesson_ids),
    ).not.toContain("candidate-nomination/advanced-stability-check");
  });

  it("keeps a bounded core route that covers each track introduction and the modelling sequence", async () => {
    const source = await sourceCurriculum();
    const core = source.learning_paths?.find((path) => path.id === "core");
    if (!core) throw new Error("core path is required");

    const introductionIds = source.tracks.map((track) => {
      const introduction = track.lessons.find(
        (lesson) => lesson.type === "intro",
      );
      if (!introduction) throw new Error(`${track.id} needs an introduction`);
      return `${track.id}/${introduction.id}`;
    });

    const selectedIntroductions = core.lesson_ids.filter((lessonId) =>
      introductionIds.includes(lessonId),
    );
    expect([...selectedIntroductions].sort()).toEqual(
      [...introductionIds].sort(),
    );
    expect(new Set(core.lesson_ids).size).toBe(core.lesson_ids.length);
    expect(core.lesson_ids).toEqual(
      expect.arrayContaining([
        "data-governance/records-to-model-table",
        "machine-learning/baseline-training-validation",
        "qsar-properties/regression-classification-errors",
        "machine-learning/student-modelling-sandbox",
      ]),
    );
  });

  it("makes specialist dependencies explicit before their mechanism lessons", async () => {
    const source = await sourceCurriculum();
    const structure = source.learning_paths?.find(
      (path) => path.id === "structure-physics",
    );
    const biologics = source.learning_paths?.find(
      (path) => path.id === "biologics",
    );
    const targets = source.learning_paths?.find(
      (path) => path.id === "targets-cells",
    );
    if (!structure || !biologics || !targets) {
      throw new Error("specialist paths are required");
    }

    expect(
      structure.lesson_ids.indexOf("physics-based-modeling/docking-to-fep"),
    ).toBeLessThan(
      structure.lesson_ids.indexOf(
        "structure-and-pockets/structure-affinity-mechanisms",
      ),
    );
    expect(biologics.prerequisites).toContain(
      "physics-based-modeling/docking-to-fep",
    );
    expect(targets.prerequisites).toContain(
      "representations/biological-representations",
    );
  });

  it("rejects a path lesson reference that is not a canonical delivered lesson", async () => {
    const source = await sourceCurriculum();
    source.learning_paths?.[0]?.lesson_ids.push("foundations/not-a-lesson");

    await expect(expectInvalid(source)).resolves.toContain(
      "learning_paths.0.lesson_ids",
    );
  });

  it("rejects a core route that puts a prerequisite after its consumer", async () => {
    const source = await sourceCurriculum();
    const core = source.learning_paths?.find((path) => path.id === "core");
    if (!core) throw new Error("core path is required");

    const learnerIndex = core.lesson_ids.indexOf("foundations/first-session");
    const prerequisiteIndex = core.lesson_ids.indexOf(
      "foundations/getting-started",
    );
    if (learnerIndex < 0 || prerequisiteIndex < 0) {
      throw new Error("core route must include the foundations entry sequence");
    }
    [core.lesson_ids[learnerIndex], core.lesson_ids[prerequisiteIndex]] = [
      core.lesson_ids[prerequisiteIndex],
      core.lesson_ids[learnerIndex],
    ];

    await expect(expectInvalid(source)).resolves.toContain(
      "learning_paths.0.lesson_ids",
    );
  });

  it("rejects a core route that omits an undeclared lesson prerequisite", async () => {
    const source = await sourceCurriculum();
    const core = source.learning_paths?.find((path) => path.id === "core");
    if (!core) throw new Error("core path is required");
    core.lesson_ids = core.lesson_ids.filter(
      (lessonId) => lessonId !== "foundations/getting-started",
    );

    await expect(expectInvalid(source)).resolves.toContain(
      "must include foundations/getting-started before foundations/first-session or declare it outside the route",
    );
  });

  it("allows a core route to declare a prerequisite outside its explicit lesson selection", async () => {
    const source = await sourceCurriculum();
    const core = source.learning_paths?.find((path) => path.id === "core");
    if (!core) throw new Error("core path is required");
    core.lesson_ids = core.lesson_ids.filter(
      (lessonId) => lessonId !== "foundations/getting-started",
    );
    core.prerequisites.push("foundations/getting-started");

    const resources = await loadCatalog("catalog/resources", {
      today: latestCurrentCalendarDate(),
    });
    const validated = await withCurriculum(source, (path) =>
      loadCurriculum(path, { resources }),
    );

    expect(
      validated.learning_paths.find((path) => path.id === "core")
        ?.prerequisites,
    ).toContain("foundations/getting-started");
  });

  it("rejects a unit prerequisite cycle", async () => {
    const source = await sourceCurriculum();
    const [first, second] = source.units ?? [];
    if (!first || !second)
      throw new Error("at least two curriculum units are required");
    first.prerequisites = [second.id];
    second.prerequisites = [first.id];

    await expect(expectInvalid(source)).resolves.toContain(
      "unit prerequisites contains a cycle",
    );
  });

  it("rejects a unit that maps to an unknown historical topic", async () => {
    const source = await sourceCurriculum();
    const [first] = source.units ?? [];
    if (!first) throw new Error("a curriculum unit is required");
    first.historical_topic_ids = ["t99-not-in-taxonomy"];

    await expect(expectInvalid(source)).resolves.toContain(
      "does not resolve to a historical taxonomy topic ID",
    );
  });

  it("uses granular teaching mechanisms rather than reusing the historical audit topics as units", async () => {
    const source = await sourceCurriculum();
    const unitIds = new Set(source.units?.map((unit) => unit.id));

    expect(
      [
        "gwas-fine-mapping",
        "colocalization-and-mendelian-randomization",
        "crispr-and-perturb-seq",
        "gnn-message-passing",
        "transformer-attention",
        "geometric-equivariance",
        "gaussian-processes",
        "force-fields-and-solvent",
        "molecular-dynamics-and-sampling",
        "relative-and-absolute-binding-free-energy",
        "qm-mm-boundaries",
        "autoregressive-generation",
        "variational-autoencoders",
        "diffusion-generation",
        "normalizing-flows",
        "antibody-design",
        "peptide-design",
        "nucleic-acid-therapeutics",
        "adc-and-degrader-modalities",
        "clearance-exposure-and-pkpd",
        "retrieval-augmented-generation",
        "tool-input-output-contracts",
        "agent-planning",
        "verifiers-and-human-review",
      ].every((unitId) => unitIds.has(unitId)),
    ).toBe(true);
    expect(unitIds.has("t12-design-objective-constraints")).toBe(false);
    expect(unitIds.has("t17-reproduction-reporting-receipt")).toBe(false);
  });

  it("renders bilingual routes, available units, and planned units without source-path lesson links", async () => {
    const source = await sourceCurriculum();
    const unitCount = source.units?.length ?? 0;
    const english = await readFile(
      join(
        siteBuildDirectory,
        "learn",
        "foundations",
        "curriculum-map",
        "index.html",
      ),
      "utf8",
    );
    const chinese = await readFile(
      join(
        siteBuildDirectory,
        "zh-cn",
        "learn",
        "foundations",
        "curriculum-map",
        "index.html",
      ),
      "utf8",
    );

    expect(english).toContain("Core AIDD evidence-to-model route");
    expect(english).toContain("Available");
    expect(english).toContain("Planned");
    expect(english.match(/data-learning-path=/g)).toHaveLength(6);
    expect(english.match(/data-curriculum-unit=/g) ?? []).toHaveLength(
      unitCount,
    );
    expect(english).toContain("data-unit-lesson");
    expect(english).toContain("Historical taxonomy mapping.");
    expect(english).toContain("t01-evidence-claim-unknown");
    expect(english).not.toContain(
      "/learn/foundations/foundations-core-source-path/",
    );
    expect(chinese).toContain("AIDD 证据到模型核心路径");
    expect(chinese).toContain("已提供");
    expect(chinese).toContain("计划中");
    expect(chinese).toContain("历史分类映射.");
    expect(chinese).toContain("你的第一次学习");
  });
});
