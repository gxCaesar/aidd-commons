import { readdir, readFile } from "node:fs/promises";
import { join } from "node:path";
import { fileURLToPath } from "node:url";

import { describe, expect, it } from "vitest";

import { parse } from "yaml";

const repositoryRoot = fileURLToPath(new URL("../..", import.meta.url));
const resourceDirectory = join(repositoryRoot, "catalog/resources");

// The metadata groups an evidence entry may establish, from
// `catalog/schema/resource.ts`. The catalogue validator enforces the same
// list, but only after a record has been written, and its message names the
// schema rather than the rule. This test is the one that says which record
// and which evidence entry are wrong.
const supportGroups = new Set([
  "name",
  "kind",
  "summary",
  "identifiers",
  "stages",
  "modalities",
  "tasks",
  "relations",
  "caveats",
  "acknowledgements",
]);

type Evidence = { id?: string; supports?: string[] };

describe("every evidence entry names only the metadata groups it can establish", () => {
  it("names no group outside the ten", async () => {
    const names = await readdir(resourceDirectory);
    const findings: string[] = [];
    for (const name of names) {
      if (!name.endsWith(".yaml")) continue;
      const record = parse(
        await readFile(join(resourceDirectory, name), "utf8"),
      ) as { evidence?: Evidence[] };
      for (const entry of record.evidence ?? []) {
        for (const group of entry.supports ?? []) {
          if (!supportGroups.has(group)) {
            findings.push(
              `${name}: evidence '${entry.id ?? "?"}' names '${group}'`,
            );
          }
        }
      }
    }
    expect(findings).toEqual([]);
  });

  it("establishes the identifiers of every record from some evidence entry", async () => {
    const names = await readdir(resourceDirectory);
    const unsupported: string[] = [];
    for (const name of names) {
      if (!name.endsWith(".yaml")) continue;
      const record = parse(
        await readFile(join(resourceDirectory, name), "utf8"),
      ) as { identifiers?: unknown[]; evidence?: Evidence[] };
      const identifiers = record.identifiers ?? [];
      if (identifiers.length === 0) continue;
      const supported = (record.evidence ?? []).some((entry) =>
        (entry.supports ?? []).includes("identifiers"),
      );
      if (!supported) unsupported.push(name);
    }
    expect(unsupported).toEqual([]);
  });
});
