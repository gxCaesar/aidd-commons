import { execFile as execFileCallback } from "node:child_process";
import { mkdtemp, readFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { promisify } from "node:util";
import { fileURLToPath } from "node:url";

import { describe, expect, it } from "vitest";
import { loadCatalog } from "../../scripts/catalog/catalog.js";

const execFile = promisify(execFileCallback);
const repositoryRoot = fileURLToPath(new URL("../..", import.meta.url));
const tsxCli = new URL("../../node_modules/tsx/dist/cli.mjs", import.meta.url);

type CommandResult = {
  exitCode: number;
  stderr: string;
  stdout: string;
};

async function runExporter(outputDirectory: string): Promise<CommandResult> {
  try {
    const { stderr, stdout } = await execFile(
      process.execPath,
      [
        tsxCli.pathname,
        "scripts/catalog/export.ts",
        "tests/catalog/fixtures/export-source",
        "--output",
        outputDirectory,
        "--today",
        "2026-09-04",
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

describe("catalog export CLI", () => {
  it("writes stable ID-sorted JSON, CSV, and openness-only projections", async () => {
    const outputDirectory = await mkdtemp(
      join(tmpdir(), "aidd-catalog-export-"),
    );
    const firstRun = await runExporter(outputDirectory);

    expect(firstRun.exitCode).toBe(0);

    const [resourcesJson, resourcesCsv, opennessJson] = await Promise.all([
      readFile(join(outputDirectory, "resources.v1.json"), "utf8"),
      readFile(join(outputDirectory, "resources.v1.csv"), "utf8"),
      readFile(join(outputDirectory, "openness.v1.json"), "utf8"),
    ]);
    const resources = JSON.parse(resourcesJson) as Array<{ id: string }>;
    const openness = JSON.parse(opennessJson) as Array<{
      evidence: Array<{ id: string; url: string }>;
      id: string;
      openness: Record<string, { evidence?: string[]; value: string }>;
    }>;

    expect(resources.map((resource) => resource.id)).toEqual([
      "alpha-resource",
      "zeta-resource",
    ]);
    expect(
      resourcesCsv
        .trimEnd()
        .split("\n")
        .slice(1)
        .map((row) => row.split(",")[0]),
    ).toEqual(["alpha-resource", "zeta-resource"]);
    expect(openness.map((record) => record.id)).toEqual([
      "alpha-resource",
      "zeta-resource",
    ]);
    expect(openness.map((record) => Object.keys(record).sort())).toEqual([
      ["evidence", "id", "openness"],
      ["evidence", "id", "openness"],
    ]);
    for (const record of openness) {
      const evidenceById = new Map(
        record.evidence.map((item) => [item.id, item.url]),
      );
      for (const claim of Object.values(record.openness)) {
        for (const evidenceId of claim.evidence ?? []) {
          expect(evidenceById.get(evidenceId)).toMatch(/^https:\/\//u);
        }
      }
    }

    const secondRun = await runExporter(outputDirectory);
    const secondContents = await Promise.all([
      readFile(join(outputDirectory, "resources.v1.json"), "utf8"),
      readFile(join(outputDirectory, "resources.v1.csv"), "utf8"),
      readFile(join(outputDirectory, "openness.v1.json"), "utf8"),
    ]);

    expect(secondRun.exitCode).toBe(0);
    expect(secondContents).toEqual([resourcesJson, resourcesCsv, opennessJson]);
  });

  it("uses ASCII ordering for digit and hyphen resource IDs", async () => {
    const originalLocaleCompare = String.prototype.localeCompare;
    String.prototype.localeCompare = function alternateLocaleCompare(other) {
      return originalLocaleCompare.call(
        String(this).replaceAll("-", "z"),
        String(other).replaceAll("-", "z"),
      );
    };

    try {
      const resources = await loadCatalog(
        "tests/catalog/fixtures/ordering-source",
        { today: "2026-09-04" },
      );

      expect(resources.map((resource) => resource.id)).toEqual([
        "atom-10",
        "atom-2",
        "atom0",
      ]);
    } finally {
      String.prototype.localeCompare = originalLocaleCompare;
    }
  });
});
