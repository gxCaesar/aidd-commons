import { glob, readFile, stat } from "node:fs/promises";
import { join, relative } from "node:path";
import { fileURLToPath } from "node:url";

import { describe, expect, it } from "vitest";

const repositoryRoot = fileURLToPath(new URL("../..", import.meta.url));
const siteBuildDirectory = join(repositoryRoot, "site", "dist");

async function builtHtmlPages() {
  const pages: string[] = [];
  for await (const page of glob("**/*.html", { cwd: siteBuildDirectory })) {
    pages.push(page);
  }
  return pages;
}

function internalLearnHrefs(document: string) {
  return Array.from(
    document.matchAll(/<a\b[^>]*\bhref=(["'])(\/learn\/[^"']*)\1/gu),
    (match) => match[2],
  );
}

function staticOutputFor(href: string) {
  const pathname = new URL(href, "https://aidd-commons.invalid").pathname;
  const route = pathname.replace(/^\/+/, "").replace(/\/?$/, "/");

  return join(siteBuildDirectory, route, "index.html");
}

describe("built internal Learn links", () => {
  it("renders only Learn anchors whose static route exists", async () => {
    const brokenLinks: Array<{ from: string; href: string; output: string }> =
      [];
    const renderedHrefs: string[] = [];

    for (const page of await builtHtmlPages()) {
      const document = await readFile(join(siteBuildDirectory, page), "utf8");
      for (const href of internalLearnHrefs(document)) {
        renderedHrefs.push(href);
        const output = staticOutputFor(href);

        try {
          await stat(output);
        } catch {
          brokenLinks.push({
            from: `/${page}`,
            href,
            output: relative(siteBuildDirectory, output),
          });
        }
      }
    }

    expect(renderedHrefs).toContain("/learn/foundations/getting-started/");
    expect(brokenLinks).toEqual([]);
  });
});
