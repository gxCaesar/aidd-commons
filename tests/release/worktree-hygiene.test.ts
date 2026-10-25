import { readFile } from "node:fs/promises";
import { fileURLToPath } from "node:url";

import { describe, expect, it } from "vitest";

const repositoryRoot = fileURLToPath(new URL("../..", import.meta.url));

describe("local package-cache hygiene", () => {
  it("ignores repository-local package caches and generated scratch files", async () => {
    const gitignore = await readFile(`${repositoryRoot}/.gitignore`, "utf8");

    expect(gitignore).toContain(".pnpm-store/");
    expect(gitignore).toContain("public-release.inventory.txt");
    expect(gitignore).toContain("release-hygiene-report.json");
    expect(gitignore).toContain("labs/chembl_egfr/results/");
    expect(gitignore).toContain("tmp/");
  });
});
