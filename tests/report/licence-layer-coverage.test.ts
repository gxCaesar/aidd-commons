import { readdir, readFile } from "node:fs/promises";
import { join } from "node:path";
import { fileURLToPath } from "node:url";

import { describe, expect, it } from "vitest";

import { parse } from "yaml";

const repositoryRoot = fileURLToPath(new URL("../..", import.meta.url));
const resourceDirectory = join(repositoryRoot, "catalog/resources");

// The access-and-licence figure sorts every record's licences into a layer,
// and it raises when a licence name is in no layer. A new licence name in the
// catalogue therefore breaks the figure build, which is a correct failure but
// an expensive one to find late. This test reports the same thing at the point
// where the record is written.
const layerNames = [
  "CC0",
  "CC0 1.0",
  "CC0 1.0 Universal",
  "CC0-1.0",
  "United States Government work, public domain",
  "MIT",
  "Apache-2.0",
  "BSD-3-Clause",
  "BSD-2-Clause",
  "ASL",
  "New BSD",
  "CC-BY-4.0",
  "CC BY 4.0",
  "CC BY-4.0",
  "Creative Commons Attribution 4.0 International",
  "Creative Commons Attribution 4.0 International Public License",
  "GPL-3.0",
  "GPL-2.0",
  "GPL-2.0 with clarifying addendum",
  "LGPL-2.1",
  "MPL-2.0",
  "GNU Affero General Public License v3",
  "CC BY-SA 4.0",
  "Creative Commons Attribution-ShareAlike 3.0 Unported",
  "CC BY-NC 4.0",
  "CC-BY-NC-ND-4.0",
  "CC BY-NC-SA 4.0",
  "Apache-2.0 with Commons Clause v1.0",
  "EMBL-EBI Terms of Use",
  "Polaris Platform Agreement",
  "The scFoundation License",
  "Other (Open)",
  "NVIDIA Open Model License",
  "Community-Spec-1.0 with CC-BY-3.0",
  "DepMap Portal Data Terms and Conditions",
  "GTEx Portal Data License",
  "DrugBank Academic License",
  "Proprietary, no open-source licence",
  "Arc Research Institute PIE Model Non-Commercial License",
];

type Resource = {
  id: string;
  licenses?: Array<{ name: string }>;
};

async function readResources(): Promise<Resource[]> {
  const names = await readdir(resourceDirectory);
  const resources: Resource[] = [];
  for (const name of names) {
    if (!name.endsWith(".yaml")) continue;
    const text = await readFile(join(resourceDirectory, name), "utf8");
    resources.push(parse(text) as Resource);
  }
  return resources;
}

describe("every licence name in the catalogue has a layer in the figure", () => {
  it("places each licence name the access figure sorts", async () => {
    const resources = await readResources();
    const unknown = new Map<string, string[]>();
    for (const resource of resources) {
      for (const licence of resource.licenses ?? []) {
        if (!layerNames.includes(licence.name)) {
          const holders = unknown.get(licence.name) ?? [];
          holders.push(resource.id);
          unknown.set(licence.name, holders);
        }
      }
    }
    const report = [...unknown.entries()]
      .map(([name, holders]) => `${name}: ${holders.join(", ")}`)
      .sort();
    expect(report).toEqual([]);
  });

  it("keeps the figure's layer list and this test's list in step", async () => {
    const figure = await readFile(
      join(repositoryRoot, "report/figures/plot_7_access_and_licence.py"),
      "utf8",
    );
    // The figure raises on a licence name that is in no layer, so a name
    // added to the catalogue and not to the figure breaks the build. This
    // test fails first, where the record is written.
    const block = figure.slice(
      figure.indexOf("LICENCE_LAYERS"),
      figure.indexOf("NO_LICENCE"),
    );
    const declared = new Set(
      Array.from(block.matchAll(/"([^"]+)"/gu), (match) => match[1]!),
    );
    const missing = layerNames.filter((name) => !declared.has(name));
    expect(missing).toEqual([]);
  });
});
