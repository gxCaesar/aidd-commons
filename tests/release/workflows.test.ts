import { readFile } from "node:fs/promises";
import { fileURLToPath } from "node:url";

import { describe, expect, it } from "vitest";
import { parse } from "yaml";

const repositoryRoot = fileURLToPath(new URL("../..", import.meta.url));

type WorkflowStep = { uses?: string; run?: string; name?: string };
type Workflow = { jobs: Record<string, { steps: WorkflowStep[] }> };

describe("CI workflow contracts", () => {
  it("builds the static site before running tests that inspect rendered routes", async () => {
    const packageManifest = JSON.parse(
      await readFile(`${repositoryRoot}/package.json`, "utf8"),
    ) as {
      scripts?: {
        check?: string;
        "comparisons:build"?: string;
        "comparisons:validate"?: string;
      };
    };
    const checkScript = packageManifest.scripts?.check ?? "";

    expect(packageManifest.scripts?.["comparisons:validate"]).toBe(
      "tsx scripts/comparisons/validate.ts",
    );
    expect(packageManifest.scripts?.["comparisons:build"]).toBe(
      "tsx scripts/comparisons/export.ts",
    );
    expect(checkScript).toContain("pnpm catalog:build");
    expect(checkScript.indexOf("pnpm comparisons:validate")).toBeGreaterThan(
      -1,
    );
    expect(checkScript.indexOf("pnpm comparisons:build")).toBeGreaterThan(
      checkScript.indexOf("pnpm comparisons:validate"),
    );
    expect(checkScript.indexOf("pnpm --dir site build")).toBeGreaterThan(-1);
    expect(checkScript.indexOf("pnpm --dir site build")).toBeGreaterThan(
      checkScript.indexOf("pnpm comparisons:build"),
    );
    expect(checkScript.indexOf("pnpm test:unit")).toBeGreaterThan(
      checkScript.indexOf("pnpm --dir site build"),
    );
  });

  it("stages pull-request checks without secrets and installs pnpm explicitly", async () => {
    const workflow = await readFile(
      `${repositoryRoot}/.github/workflows/ci.yml`,
      "utf8",
    );

    expect(workflow).toContain("pull_request:");
    expect(workflow).toContain("contents: read");
    expect(workflow).not.toMatch(/\bsecrets\./iu);
    expect(workflow).toContain("pnpm/setup@v2");
    expect(workflow).toContain("runtime: node@24");
    expect(workflow).toContain("install: false");
    expect(
      workflow.match(
        /- uses: pnpm\/setup@v2\n\s+with:\n\s+runtime: node@24\n\s+install: false/gu,
      ),
    ).toHaveLength(5);
    expect(workflow).not.toContain("require-lockfile: true");
    expect(workflow).toContain("if [ -f pnpm-lock.yaml ]; then");
    expect(workflow).toContain("pnpm install --no-frozen-lockfile");
    expect(workflow).toContain("if [ -f uv.lock ]; then");
    expect(workflow).toContain("uv sync --group dev");
    expect(workflow).toContain("pnpm comparisons:validate");
    expect(workflow).toContain("pnpm exec vitest run tests/comparisons");
    expect(workflow).toContain("pnpm comparisons:build");
    expect(workflow.indexOf("pnpm comparisons:validate")).toBeLessThan(
      workflow.indexOf("pnpm comparisons:build"),
    );
    for (const stage of [
      "catalog:",
      "web:",
      "links-and-citations:",
      "python-labs:",
      "browser-and-accessibility:",
      "release-hygiene:",
    ]) {
      expect(workflow).toContain(stage);
    }
  });

  it("keeps external link availability scheduled and non-blocking", async () => {
    const workflow = await readFile(
      `${repositoryRoot}/.github/workflows/external-links.yml`,
      "utf8",
    );

    expect(workflow).toContain("schedule:");
    expect(workflow).toContain("continue-on-error: true");
    expect(workflow).toContain("pnpm/setup@v2");
    expect(
      workflow.match(
        /- uses: pnpm\/setup@v2\n\s+with:\n\s+runtime: node@24\n\s+install: false/gu,
      ),
    ).toHaveLength(1);
    expect(workflow).toContain("pnpm install --no-frozen-lockfile");
    expect(workflow).toContain("artifacts/external-links.json");
    expect(workflow).not.toContain("pull_request:");
  });

  it("installs Python dependencies before every site build and export test", async () => {
    const workflow = parse(
      await readFile(`${repositoryRoot}/.github/workflows/ci.yml`, "utf8"),
    ) as Workflow;
    for (const name of [
      "web",
      "links-and-citations",
      "browser-and-accessibility",
      "release-hygiene",
    ]) {
      const steps = workflow.jobs[name].steps;
      const python = steps.findIndex((step) =>
        step.uses?.startsWith("actions/setup-python@"),
      );
      const uv = steps.findIndex((step) =>
        step.run?.includes("pip install --disable-pip-version-check uv"),
      );
      const sync = steps.findIndex((step) =>
        step.run?.includes("uv sync --group dev"),
      );
      const consumer = steps.findIndex((step) =>
        /(?:pnpm --dir site (?:check|build)|python -m pytest labs\/tests)/u.test(
          step.run ?? "",
        ),
      );
      expect(python, `${name}: Python is required`).toBeGreaterThan(-1);
      expect(uv, `${name}: uv is required`).toBeGreaterThan(python);
      expect(
        sync,
        `${name}: the figure/test dependencies are required`,
      ).toBeGreaterThan(uv);
      expect(consumer, `${name}: setup must precede use`).toBeGreaterThan(sync);
    }
  });

  it("deploys only a verified curated build on a main-branch push", async () => {
    const workflow = await readFile(
      `${repositoryRoot}/.github/workflows/ci.yml`,
      "utf8",
    );
    const jobs = (
      parse(workflow) as {
        jobs: Record<
          string,
          { needs?: string; if?: string; steps: WorkflowStep[] }
        >;
      }
    ).jobs;
    const release = jobs["release-hygiene"].steps;
    const build = release.findIndex(
      (step) => step.name === "Build the Pages site from the curated export",
    );
    const test = release.findIndex(
      (step) => step.name === "Test the export against its own code",
    );
    expect(build).toBeGreaterThan(test);
    expect(release[build].run).toContain("check-internal-links.ts site/dist");
    expect(jobs["deploy-pages"].needs).toBe("release-hygiene");
    expect(jobs["deploy-pages"].if).toBe(
      "github.event_name == 'push' && github.ref == 'refs/heads/main'",
    );
    expect(workflow).toContain(
      "AIDD_BASE_PATH: /${{ github.event.repository.name }}",
    );
    expect(workflow).toContain("uses: actions/deploy-pages@v5");
  });
});
