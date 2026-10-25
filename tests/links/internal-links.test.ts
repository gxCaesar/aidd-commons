import { mkdir, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { mkdtemp } from "node:fs/promises";

import { describe, expect, it } from "vitest";

async function builtSiteWithOneBrokenLink(): Promise<string> {
  const directory = await mkdtemp(join(tmpdir(), "aidd-internal-links-"));
  await mkdir(join(directory, "existing"), { recursive: true });
  await Promise.all([
    writeFile(
      join(directory, "index.html"),
      '<a href="/existing/">existing</a><a href="/missing/">missing</a><a href="https://example.org/">external</a>',
    ),
    writeFile(join(directory, "existing", "index.html"), "<p>existing</p>"),
  ]);
  return directory;
}

describe("built internal link checker", () => {
  it("reports only unresolved internal anchor routes", async () => {
    const { findBrokenInternalLinks } = await import(
      "../../scripts/quality/check-internal-links.js"
    );
    const directory = await builtSiteWithOneBrokenLink();

    await expect(findBrokenInternalLinks(directory)).resolves.toEqual([
      {
        from: "/index.html",
        href: "/missing/",
        output: "missing/index.html",
      },
    ]);
  });

  it("resolves prefixed and relative links within a project deployment", async () => {
    const { findBrokenInternalLinks } = await import(
      "../../scripts/quality/check-internal-links.js"
    );
    const directory = await builtSiteWithOneBrokenLink();
    await writeFile(
      join(directory, "index.html"),
      '<a href="/aidd-commons/existing/">prefixed</a><a href="existing/">relative</a>',
    );
    await expect(
      findBrokenInternalLinks(directory, "/aidd-commons/"),
    ).resolves.toEqual([]);
  });

  it("reports links that escape a project deployment even when the target file exists", async () => {
    const { findBrokenInternalLinks } = await import(
      "../../scripts/quality/check-internal-links.js"
    );
    const directory = await builtSiteWithOneBrokenLink();
    await writeFile(
      join(directory, "index.html"),
      '<a href="/existing/">unprefixed</a>',
    );
    await expect(
      findBrokenInternalLinks(directory, "/aidd-commons/"),
    ).resolves.toEqual([
      {
        from: "/index.html",
        href: "/existing/",
        output: "outside deployment base /aidd-commons/",
      },
    ]);
  });
});
