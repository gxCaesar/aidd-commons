import { readFile } from "node:fs/promises";
import { join } from "node:path";
import { fileURLToPath } from "node:url";

import { describe, expect, it } from "vitest";

const repositoryRoot = fileURLToPath(new URL("../..", import.meta.url));

async function read(relativePath: string) {
  return readFile(join(repositoryRoot, relativePath), "utf8");
}

describe("comparison audit page", () => {
  it("makes the external freeze and separate current product review visible", async () => {
    const page = await read("site/src/pages/audit/index.astro");
    expect(page).toContain("data-comparison-date-boundary");
    expect(page).toContain("comparison.external_survey_frozen_on");
    expect(page).toContain("CURRENT_RESOURCE_COMPARISON.md");
    expect(page).toContain("without rescoring this matrix");
  });

  it("publishes bounded coverage without collapsing it into an overall score", async () => {
    const [page, bounds, matrix] = await Promise.all([
      read("site/src/pages/audit/index.astro"),
      read("site/src/components/CoverageBounds.astro"),
      read("site/src/components/ComparisonMatrix.astro"),
    ]);
    const surface = [page, bounds, matrix].join("\n");

    expect(surface).toContain("Lower bound");
    expect(surface).toContain("Upper bound");
    expect(surface).toContain("not established");
    expect(surface).not.toMatch(/overall score/iu);
  });

  it("keeps filters, cell state, and evidence available to assistive technology", async () => {
    const matrix = await read("site/src/components/ComparisonMatrix.astro");

    expect(matrix).toContain("<table");
    expect(matrix).toContain("<select");
    expect(matrix).toContain("<details");
    expect(matrix).toContain('data-label="Evidence"');
    expect(matrix).toContain("Direct observations only");
    for (const [id, filter] of [
      ["comparison-track", "Track"],
      ["comparison-topic", "Topic"],
      ["comparison-provider-class", "Provider class"],
      ["comparison-depth", "Coverage depth"],
      ["comparison-access", "Content access"],
      ["comparison-language", "Language"],
      ["comparison-review-after", "Reviewed on or after"],
    ]) {
      expect(matrix).toContain(`<label for="${id}">${filter}</label>`);
    }
    expect(matrix).not.toMatch(/onmouseover|onmouseenter/iu);
  });

  it("distinguishes confirmed gaps from topics requiring self-audit", async () => {
    const page = await read("site/src/pages/audit/index.astro");

    expect(page).toContain("Confirmed depth gaps");
    expect(page).toContain("Self-audit needed");
    expect(page).toContain("must not be interpreted as a confirmed deficiency");
    // With no confirmed gap the section must say so rather than render an empty
    // list, and must not read as a claim that unverified topics are covered.
    // Match the whole rendered sentence inside its own conditional block, not
    // disjoint substrings that could each appear somewhere unrelated.
    const emptyStateBlock = page.match(
      /comparison\.gaps\.candidates\.length === 0[\s\S]{0,400}?<\/p>/u,
    )?.[0];
    expect(emptyStateBlock).toBeDefined();
    expect(emptyStateBlock).toContain("data-gap-empty");
    expect(emptyStateBlock).toContain(
      "No evidence-backed depth gap is identified in the current records",
    );
    expect(emptyStateBlock).toContain(
      "it says nothing\n        about topics still recorded as unverified",
    );
  });

  it("distinguishes the frozen selection contract from live delivery", async () => {
    const page = await read("site/src/pages/audit/index.astro");

    expect(page).toContain("Frozen v0.2b depth candidates");
    expect(page).toContain("Independent unit");
    expect(page).toContain("Cheap baseline");
    expect(page).toContain(
      "implementation status and result note describe current delivery",
    );
  });

  it("links the audit from both site navigation systems", async () => {
    const [shell, starlight] = await Promise.all([
      read("site/dist/index.html"),
      read("site/dist/learn/foundations/getting-started/index.html"),
    ]);

    for (const document of [shell, starlight]) {
      const navigation = [...document.matchAll(/<nav\b[^>]*>[\s\S]*?<\/nav>/gu)]
        .map((match) => match[0])
        .join("\n");
      expect(navigation).toMatch(
        /<a\b[^>]*href="\/audit\/"[^>]*>[\s\S]*?Audit[\s\S]*?<\/a>/u,
      );
    }
  });
});
