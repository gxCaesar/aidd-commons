import { readFile } from "node:fs/promises";
import { join } from "node:path";
import { fileURLToPath } from "node:url";

import { describe, expect, it } from "vitest";

const repositoryRoot = fileURLToPath(new URL("../..", import.meta.url));
const siteBuildDirectory = join(repositoryRoot, "site", "dist");
const productAreas = [
  ["Learn", "/learn/foundations/getting-started/"],
  ["Atlas", "/atlas/"],
  ["Labs", "/labs/"],
  ["Audit", "/audit/"],
  ["Report", "/report/"],
  ["Contribute", "/contribute/"],
] as const;

function starlightSidebar(document: string) {
  const start = document.indexOf('<nav class="sidebar');
  const end = document.indexOf("</nav>", start);

  return document.slice(start, end + "</nav>".length);
}

describe("Starlight product navigation", () => {
  it.each([
    "atlas/freesolv-v0-52/index.html",
    "learn/foundations/getting-started/index.html",
  ])("keeps every product area reachable from %s", async (page) => {
    const document = await readFile(join(siteBuildDirectory, page), "utf8");
    const sidebar = starlightSidebar(document);

    expect(sidebar).toContain('aria-label="Main"');
    for (const [label, href] of productAreas) {
      expect(sidebar).toContain(`href="${href}"`);
      expect(sidebar).toContain(`>${label}<`);
    }
  });
});
