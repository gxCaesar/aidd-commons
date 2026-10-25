import { readFileSync, readdirSync } from "node:fs";
import { resolve } from "node:path";

import { describe, expect, it } from "vitest";
import { parse } from "yaml";

const root = resolve(import.meta.dirname, "../..");
const templateDirectory = resolve(root, ".github/ISSUE_TEMPLATE");

const expectedTemplates = [
  "correction.yml",
  "experiment-report.yml",
  "lab-proposal.yml",
  "lesson-proposal.yml",
  "rfc.yml",
  "source-proposal.yml",
];

const requiredFieldIds = [
  "summary",
  "evidence",
  "licence_attribution",
  "audience",
  "scientific_assumptions",
  "conflict_disclosure",
];

describe("contribution forms", () => {
  it("provides the editorial forms and the learner question form", () => {
    expect(
      readdirSync(templateDirectory)
        .filter((name) => name.endsWith(".yml"))
        .sort(),
    ).toEqual([...expectedTemplates, "learning-question.yml"].sort());
  });

  it("lets learners ask with a location and question while keeping an attempted answer optional", () => {
    const form = parse(
      readFileSync(resolve(templateDirectory, "learning-question.yml"), "utf8"),
    );
    const fields = new Map(
      form.body
        .filter((field: { id?: string }) => field.id)
        .map((field: { id: string; validations?: { required?: boolean } }) => [
          field.id,
          field,
        ]),
    );
    expect([...fields.keys()]).toEqual([
      "location",
      "question",
      "reasoning",
      "execution",
    ]);
    for (const id of ["location", "question"]) {
      expect(fields.get(id)).toMatchObject({ validations: { required: true } });
    }
    for (const id of ["reasoning", "execution"]) {
      expect(fields.get(id)).toMatchObject({
        validations: { required: false },
      });
    }
  });

  it.each(expectedTemplates)(
    "%s is parseable and asks for the editorial evidence contract",
    (name) => {
      const source = readFileSync(resolve(templateDirectory, name), "utf8");
      const form = parse(source) as {
        name?: string;
        description?: string;
        body?: Array<{
          id?: string;
          type?: string;
          attributes?: { label?: string };
        }>;
      };

      expect(form.name).toBeTruthy();
      expect(form.description).toBeTruthy();
      expect(Array.isArray(form.body)).toBe(true);

      const ids = new Set(
        (form.body ?? []).map((field) => field.id).filter(Boolean),
      );
      for (const id of requiredFieldIds) {
        expect(ids, `${name} is missing ${id}`).toContain(id);
      }

      const inputIds = [...ids].join(" ");
      expect(inputIds).not.toMatch(
        /checksum|digest|prompt|credential|receipt/i,
      );
    },
  );

  it("publishes the contributor, governance, safety, attribution, and citation surfaces", () => {
    const requiredFiles = [
      "CONTRIBUTING.md",
      "GOVERNANCE.md",
      "CODE_OF_CONDUCT.md",
      "SECURITY.md",
      "CITATION.cff",
      "THIRD_PARTY_NOTICES.md",
      "ACKNOWLEDGEMENTS.md",
      ".github/PULL_REQUEST_TEMPLATE.md",
      "docs/EDITORIAL_GUIDE.md",
    ];

    for (const path of requiredFiles) {
      expect(
        () => readFileSync(resolve(root, path), "utf8"),
        path,
      ).not.toThrow();
    }
  });
});
