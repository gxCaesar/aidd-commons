import { execFile as execFileCallback } from "node:child_process";
import { promisify } from "node:util";
import { fileURLToPath } from "node:url";

import { describe, expect, it } from "vitest";

import { loadCatalog } from "../../scripts/catalog/catalog.js";
import {
  expectedTrackIds,
  loadCurriculum,
} from "../../scripts/curriculum/curriculum.js";

const execFile = promisify(execFileCallback);
const repositoryRoot = fileURLToPath(new URL("../..", import.meta.url));
const tsxCli = new URL("../../node_modules/tsx/dist/cli.mjs", import.meta.url);

type CommandResult = {
  exitCode: number;
  stderr: string;
  stdout: string;
};

async function runCurriculumValidator(input: string): Promise<CommandResult> {
  try {
    const { stderr, stdout } = await execFile(
      process.execPath,
      [
        tsxCli.pathname,
        "scripts/curriculum/validate.ts",
        input,
        "--catalog",
        "catalog/resources",
      ],
      { cwd: repositoryRoot },
    );
    return { exitCode: 0, stderr, stdout };
  } catch (error) {
    const commandError = error as {
      code?: number;
      stderr?: string;
      stdout?: string;
    };
    return {
      exitCode: commandError.code ?? 1,
      stderr: commandError.stderr ?? "",
      stdout: commandError.stdout ?? "",
    };
  }
}

describe("curriculum graph", () => {
  it("defines every charter track in order with resolvable source and prerequisite references", async () => {
    const resources = await loadCatalog("catalog/resources");
    const curriculum = await loadCurriculum("catalog/curriculum/tracks.yaml", {
      resources,
    });

    expect(curriculum.tracks.map((track) => track.id)).toEqual(
      expectedTrackIds,
    );
    expect(curriculum.tracks).toHaveLength(18);
    expect(
      curriculum.tracks.every((track) => track.learning_outcomes.length >= 2),
    ).toBe(true);
    expect(curriculum.tracks.every((track) => track.lessons.length >= 2)).toBe(
      true,
    );
    expect(
      curriculum.tracks.every((track) =>
        track.lessons.some((lesson) => lesson.type === "intro"),
      ),
    ).toBe(true);
  });

  it("rejects a curriculum lesson whose prerequisite does not exist", async () => {
    const result = await runCurriculumValidator(
      "tests/curriculum/fixtures/bad-missing-prerequisite.yaml",
    );

    expect(result.exitCode).not.toBe(0);
    expect(result.stderr).toContain(
      "tests/curriculum/fixtures/bad-missing-prerequisite.yaml: tracks.0.lessons.0.prerequisites.0:",
    );
  });

  it("accepts a prerequisite from track 10 when used by track 11", async () => {
    const result = await runCurriculumValidator(
      "tests/curriculum/fixtures/valid-cross-boundary-prerequisite.yaml",
    );

    expect(result.exitCode).toBe(0);
    expect(result.stdout).toContain("Validated 18 curriculum tracks.");
  });
});
