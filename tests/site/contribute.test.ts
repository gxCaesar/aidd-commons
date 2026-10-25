import { readFile } from "node:fs/promises";
import { resolve } from "node:path";

import { describe, expect, it } from "vitest";
import { parse } from "yaml";

const root = resolve(import.meta.dirname, "../..");

describe("public contribution routes", () => {
  it("connects learning questions and contribution actions to actual public issue forms", async () => {
    const [source, publication] = await Promise.all([
      readFile(resolve(root, "site/src/pages/contribute/index.astro"), "utf8"),
      readFile(resolve(root, "catalog/comparisons/publication.json"), "utf8"),
    ]);
    const repository = new URL(JSON.parse(publication).repository_url);
    // Inspect actual literal links in page markup, excluding frontmatter and
    // commented examples that cannot provide a reader with an action.
    const markup = source
      .split("---")
      .slice(2)
      .join("---")
      .replace(/<!--[\s\S]*?-->/g, "");
    const links = [
      ...markup.matchAll(/<a\b[^>]*\bhref="([^"]*)"[^>]*>([\s\S]*?)<\/a>/g),
    ];
    const templateLinks = links.filter(([, href]) =>
      href?.includes("template="),
    );
    const templates = [
      "learning-question.yml",
      "source-proposal.yml",
      "correction.yml",
      "lesson-proposal.yml",
      "lab-proposal.yml",
      "experiment-report.yml",
      "rfc.yml",
    ];

    expect(templateLinks).toHaveLength(templates.length);
    const linkedTemplates: string[] = [];
    for (const [, href, label] of templateLinks) {
      const url = new URL(href!);
      expect(url.protocol).toBe("https:");
      expect(url.origin).toBe(repository.origin);
      expect(url.pathname).toBe(`${repository.pathname}/issues/new`);
      expect(label!.replace(/<[^>]+>/g, "").trim()).not.toBe("");
      const template = url.searchParams.get("template")!;
      expect(templates).toContain(template);
      linkedTemplates.push(template);
      const form = parse(
        await readFile(
          resolve(root, ".github/ISSUE_TEMPLATE", template),
          "utf8",
        ),
      );
      expect(form.name).toEqual(expect.any(String));
      expect(form.body.length).toBeGreaterThan(0);
    }
    expect(linkedTemplates.sort()).toEqual(templates.sort());
    expect(links.every(([, href]) => href !== "" && href !== "#")).toBe(true);
    expect(markup).not.toContain("/discussions");
  });
});
