import { readFile } from "node:fs/promises";
import { join } from "node:path";
import { fileURLToPath } from "node:url";

import { describe, expect, it } from "vitest";

const repositoryRoot = fileURLToPath(new URL("../..", import.meta.url));
const publicDirectory = join(repositoryRoot, "site", "public");

describe("public discovery metadata", () => {
  it("publishes a permissive robots policy", async () => {
    const robots = await readFile(join(publicDirectory, "robots.txt"), "utf8");

    expect(robots).toContain("User-agent: *");
    expect(robots).toContain("Allow: /");
  });

  it("publishes agent entry links to each product area", async () => {
    const llms = await readFile(join(publicDirectory, "llms.txt"), "utf8");

    expect(llms).toMatch(/^# AIDD Commons/m);
    for (const [label, href] of [
      ["Learn", "/learn/foundations/getting-started/"],
      ["Atlas", "/atlas/"],
      ["Labs", "/labs/"],
      ["Audit", "/audit/"],
      ["Report", "/report/"],
      ["Contribute", "/contribute/"],
    ]) {
      expect(llms).toContain(`[${label}](${href})`);
    }
  });
});
