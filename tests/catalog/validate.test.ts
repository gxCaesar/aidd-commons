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
        "scripts/catalog/validate.ts",
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

describe("catalog validation CLI", () => {
  it("accepts a minimal unverified resource record", async () => {
    const result = await runValidator(
      "tests/catalog/fixtures/example-aidd-resource.yaml",
    );

    expect(result.exitCode).toBe(0);
    expect(result.stdout).toContain("Validated 1 resource");
  });

  it("accepts evidence-backed status, access, openness, and licence claims", async () => {
    const result = await runValidator(
      "tests/catalog/fixtures/valid-claim-backed.yaml",
    );

    expect(result.exitCode).toBe(0);
  });

  it.each([
    ["bad-missing-status-evidence.yaml", "status.evidence"],
    ["bad-missing-openness-evidence.yaml", "openness.inference_code.evidence"],
    ["bad-missing-licence-evidence.yaml", "licenses.0.evidence"],
    ["bad-invalid-enum.yaml", "status.value"],
    ["bad-unresolved-relation.yaml", "relations.0.target"],
    ["bad-future-last-verified.yaml", "last_verified"],
    ["bad-invalid-id.yaml", "id"],
    ["bad-unsupported-url.yaml", "canonical_url"],
    ["bad-malformed-url.yaml", "canonical_url"],
    ["bad-unsupported-summary.yaml", "summary"],
    ["bad-unsupported-classification.yaml", "stages"],
    ["bad-unknown-evidence-support.yaml", "evidence.0.supports.0"],
    ["bad-empty-evidence-support.yaml", "evidence.0.supports.6"],
  ])("rejects %s at %s", async (fixtureName, field) => {
    const result = await runValidator(`tests/catalog/fixtures/${fixtureName}`);

    expect(result.exitCode).not.toBe(0);
    expect(result.stderr).toContain(
      `tests/catalog/fixtures/${fixtureName}: ${field}:`,
    );
  });
});
