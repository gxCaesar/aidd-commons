import { execFile as execFileCallback } from "node:child_process";
import { promisify } from "node:util";
import { fileURLToPath } from "node:url";

import { describe, expect, it } from "vitest";

const execFile = promisify(execFileCallback);
const repositoryRoot = fileURLToPath(new URL("../..", import.meta.url));
const tsxCli = new URL("../../node_modules/tsx/dist/cli.mjs", import.meta.url);

type CommandResult = {
  exitCode: number;
  stderr: string;
  stdout: string;
};

async function runValidator(input: string): Promise<CommandResult> {
  try {
    const { stderr, stdout } = await execFile(
      process.execPath,
      [
        tsxCli.pathname,
        "scripts/comparisons/validate.ts",
        input,
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

describe("comparison validation CLI", () => {
  it("accepts an evidence-backed system with an explicit omission default", async () => {
    const result = await runValidator(
      "tests/comparisons/fixtures/valid-repository-evidence.yaml",
    );

    expect(result).toMatchObject({ exitCode: 0, stderr: "" });
    expect(result.stdout).toContain("Validated 1 comparison system.");
  });

  it("rejects an incomplete system without an omission default", async () => {
    const result = await runValidator(
      "tests/comparisons/fixtures/valid-minimal.yaml",
    );

    expect(result.exitCode).toBe(1);
    expect(result.stderr).toContain("coverage_default");
  });
});
