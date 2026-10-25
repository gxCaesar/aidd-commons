import { readdir, readFile } from "node:fs/promises";
import { join } from "node:path";
import { fileURLToPath } from "node:url";

import { describe, expect, it } from "vitest";

import { parse } from "yaml";

const repositoryRoot = fileURLToPath(new URL("../..", import.meta.url));
const resourceDirectory = join(repositoryRoot, "catalog/resources");
const contentRoot = join(repositoryRoot, "site/src/content/docs");

type Resource = {
  id: string;
  name: string;
  canonical_url: string;
};

// A record that nothing in the published material mentions is a record a
// reader cannot find. The project has held every record to a lesson since
// 2026-10-23, and a new record that arrives without one breaks that.
async function loadResources(): Promise<Resource[]> {
  const names = await readdir(resourceDirectory);
  const resources: Resource[] = [];
  for (const name of names) {
    if (!name.endsWith(".yaml")) continue;
    const text = await readFile(join(resourceDirectory, name), "utf8");
    resources.push(parse(text) as Resource);
  }
  return resources;
}

async function publishedEnglishProse(): Promise<string> {
  const parts: string[] = [];
  for (const directory of ["learn", "labs", "atlas", "report"]) {
    const root = join(contentRoot, directory);
    const stack = [root];
    while (stack.length > 0) {
      const current = stack.pop()!;
      for (const entry of await readdir(current, { withFileTypes: true })) {
        const path = join(current, entry.name);
        if (entry.isDirectory()) {
          stack.push(path);
          continue;
        }
        if (!entry.name.endsWith(".mdx") && !entry.name.endsWith(".md")) continue;
        parts.push(await readFile(path, "utf8"));
      }
    }
  }
  return parts.join("\n");
}

describe("every catalogue record is reachable from the published material", () => {
  it("names each record in a lesson, a lab guide or an atlas page", async () => {
    const resources = await loadResources();
    const prose = await publishedEnglishProse();
    const unreached = resources
      .filter(
        (resource) =>
          !prose.includes(resource.name) && !prose.includes(resource.canonical_url),
      )
      .map((resource) => `${resource.id} (${resource.name})`);
    expect(unreached).toEqual([]);
  });
});
