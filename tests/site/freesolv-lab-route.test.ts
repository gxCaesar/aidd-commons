import { readFile } from "node:fs/promises";
import { join } from "node:path";
import { fileURLToPath } from "node:url";

import { describe, expect, it } from "vitest";

const repositoryRoot = fileURLToPath(new URL("../..", import.meta.url));
const labRoute = "/labs/freesolv-honest-baselines/";

describe("FreeSolv completed lab route", () => {
  it("publishes the frozen scaffold-primary result with its evidence limits", async () => {
    const page = await readFile(
      join(
        repositoryRoot,
        "site",
        "src",
        "content",
        "docs",
        "labs",
        "freesolv-honest-baselines.mdx",
      ),
      "utf8",
    );

    expect(page).toContain("title: FreeSolv v0.52 honest baselines");
    expect(page).toContain("Scaffold-primary results");
    expect(page).toContain("1.1280482645936036");
    expect(page).toContain("1.7597471244251413");
    expect(page).toContain("1.2568836078869037");
    expect(page).toContain("2.0375968699271554");
    expect(page).toContain("one final test evaluation");
    expect(page).toContain("does not declare licence terms");
    expect(page).toContain("does not make a SOTA claim");
  });

  it("links the Labs index to the completed Starlight route instead of a preparation claim", async () => {
    const index = await readFile(
      join(repositoryRoot, "site", "src", "pages", "labs", "index.astro"),
      "utf8",
    );

    expect(index).toContain(`href="${labRoute}"`);
    expect(index).toContain("Completed frozen protocol");
    expect(index).not.toContain("Frozen protocol in preparation");
    expect(index).toContain(
      'class="button-secondary" href="/labs/freesolv-honest-baselines/"',
    );
  });

  it("builds the lab route with exactly one title heading", async () => {
    const document = await readFile(
      join(
        repositoryRoot,
        "site",
        "dist",
        "labs",
        "freesolv-honest-baselines",
        "index.html",
      ),
      "utf8",
    );

    expect(document.match(/<h1\b/g)).toHaveLength(1);
    expect(document).toContain("FreeSolv v0.52 honest baselines");
  });
});
