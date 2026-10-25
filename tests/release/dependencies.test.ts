import { readFile } from "node:fs/promises";
import { fileURLToPath } from "node:url";

import { describe, expect, it } from "vitest";

const repositoryRoot = fileURLToPath(new URL("../..", import.meta.url));

function requirementsInArray(
  toml: string,
  header: string,
  property: string,
): string[] {
  const section = toml.match(
    new RegExp(
      `^\\[${header}\\][\\s\\S]*?^${property} = \\[([\\s\\S]*?)^\\]`,
      "mu",
    ),
  );
  if (section === null) {
    return [];
  }
  return Array.from(section[1].matchAll(/"([^"]+)"/gu), (match) => match[1]);
}

describe("public lockfile-free Python dependencies", () => {
  it("pins every direct project and development dependency exactly", async () => {
    const pyproject = await readFile(
      `${repositoryRoot}/pyproject.toml`,
      "utf8",
    );
    const requirements = [
      ...requirementsInArray(pyproject, "project", "dependencies"),
      ...requirementsInArray(pyproject, "dependency-groups", "dev"),
    ];

    expect(requirements).not.toEqual([]);
    for (const requirement of requirements) {
      expect(requirement).toMatch(
        /^[A-Za-z0-9_.-]+(?:\[[A-Za-z0-9_.,-]+\])?==[A-Za-z0-9+_.-]+$/u,
      );
    }
  });

  it("uses the exact supported pnpm package manager release", async () => {
    const packageManifest = JSON.parse(
      await readFile(`${repositoryRoot}/package.json`, "utf8"),
    ) as { packageManager?: string };

    expect(packageManifest.packageManager).toBe("pnpm@11.13.1");
  });
});
