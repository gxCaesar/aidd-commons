import { readFile } from "node:fs/promises";
import { join } from "node:path";
import { fileURLToPath } from "node:url";

import { describe, expect, it } from "vitest";

import playwrightConfig from "../../playwright.config.js";
import { validateRmd17DevelopmentSummary } from "../../site/src/lib/rmd17-development-summary.js";

const repositoryRoot = fileURLToPath(new URL("../..", import.meta.url));
const labRoute = "/labs/rmd17-system-state-energy-baselines/";

type DevelopmentSummary = {
  aggregates: Record<string, { mae_range: number; median_mae: number }>;
  development_evaluation: Record<
    string,
    {
      ridge: { mae: number; rmse: number; target_range: number };
      train_mean: { mae: number; rmse: number; target_range: number };
    }
  >;
  features: {
    bins_per_channel: number;
    by_system: Record<string, { feature_dimension: number }>;
  };
  locked_evaluations: Record<string, string>;
  selection: { selected_alpha: number };
};

describe("rMD17 development lab route", () => {
  it("wires the reviewed summary into the current lab source and Labs card", async () => {
    const [summaryText, component, labPage, labsIndex] = await Promise.all([
      readFile(
        join(
          repositoryRoot,
          "labs",
          "rmd17_system_state",
          "development-summary.json",
        ),
        "utf8",
      ),
      readFile(
        join(
          repositoryRoot,
          "site",
          "src",
          "components",
          "Rmd17DevelopmentPanel.astro",
        ),
        "utf8",
      ),
      readFile(
        join(
          repositoryRoot,
          "site",
          "src",
          "content",
          "docs",
          "labs",
          "rmd17-system-state-energy-baselines.mdx",
        ),
        "utf8",
      ),
      readFile(
        join(repositoryRoot, "site", "src", "pages", "labs", "index.astro"),
        "utf8",
      ),
    ]);
    const summary = JSON.parse(summaryText) as DevelopmentSummary;

    expect(labPage).toContain("title: rMD17 system-state energy baselines");
    expect(labPage).toContain("<Rmd17DevelopmentPanel />");
    expect(component).toContain(
      'import developmentSummary from "../../../labs/rmd17_system_state/development-summary.json";',
    );
    expect(component).toContain(
      'import { validateRmd17DevelopmentSummary } from "../lib/rmd17-development-summary.js";',
    );
    expect(component).toContain(
      "const summary = validateRmd17DevelopmentSummary(developmentSummary);",
    );
    expect(component).toContain("data-rmd17-development-panel");
    expect(component).toContain("summary.selection.selected_alpha");
    for (const aggregate of Object.values(summary.aggregates)) {
      expect(component).not.toContain(String(aggregate.median_mae));
      expect(component).not.toContain(String(aggregate.mae_range));
    }
    for (const evaluation of Object.values(summary.development_evaluation)) {
      for (const metrics of [evaluation.train_mean, evaluation.ridge]) {
        expect(component).not.toContain(String(metrics.mae));
        expect(component).not.toContain(String(metrics.rmse));
        expect(component).not.toContain(String(metrics.target_range));
      }
    }
    const ordinaryBins = summary.features.bins_per_channel - 1;
    const overflowBins = summary.features.bins_per_channel - ordinaryBins;
    expect(component).toContain("ordinaryBinCount");
    expect(component).toContain("overflowBinCount");
    expect(ordinaryBins).toBe(100);
    expect(overflowBins).toBe(1);
    expect(component).toContain("preserves an ordering cue");
    expect(component).toContain("selected frames per development system");
    expect(labPage).toContain(
      "The five source-provided train/test CSV pairs are not used",
    );
    expect(labPage).not.toContain("Original-index chronology");
    expect(labPage).not.toContain("harder descriptive challenge");
    expect(labPage).not.toContain("before any locked-evaluation statement");
    expect(labPage).not.toContain("development_evaluation_complete");
    for (const [systemId, feature] of Object.entries(
      summary.features.by_system,
    )) {
      expect(summary.development_evaluation).toHaveProperty(systemId);
      expect(feature.feature_dimension).toBeGreaterThan(0);
    }
    for (const [systemId, status] of Object.entries(
      summary.locked_evaluations,
    )) {
      expect(summary.locked_evaluations[systemId]).toBe(status);
    }
    expect(component).not.toContain("locked-metrics.json");
    expect(labsIndex).toContain(`href="${labRoute}"`);
    expect(labsIndex).toContain("Benzene and uracil evaluations completed");
  });

  it("forces a fresh Astro build before the browser preview starts", async () => {
    const sitePackage = JSON.parse(
      await readFile(join(repositoryRoot, "site", "package.json"), "utf8"),
    ) as { scripts: Record<string, string> };
    const webServer = Array.isArray(playwrightConfig.webServer)
      ? playwrightConfig.webServer[0]
      : playwrightConfig.webServer;

    expect(sitePackage.scripts.prepreview).toBe("astro build");
    expect(webServer?.command).toContain("npm --prefix site run preview");
    expect(webServer?.reuseExistingServer).toBe(false);
  });

  it("fails closed when the reviewed summary loses a required system", async () => {
    const valid = JSON.parse(
      await readFile(
        join(
          repositoryRoot,
          "labs",
          "rmd17_system_state",
          "development-summary.json",
        ),
        "utf8",
      ),
    ) as Record<string, unknown>;

    expect(validateRmd17DevelopmentSummary(valid)).toMatchObject({
      artifact_type: "reviewed-development-summary",
      development_evaluation: {
        ethanol: expect.any(Object),
        malonaldehyde: expect.any(Object),
      },
      locked_evaluations: { benzene: "not_run", uracil: "not_run" },
    });

    const noDevelopmentSystems = structuredClone(valid);
    noDevelopmentSystems.development_evaluation = {};
    expect(() => validateRmd17DevelopmentSummary(noDevelopmentSystems)).toThrow(
      "development_evaluation must contain exactly ethanol, malonaldehyde",
    );

    const oneLockedSystem = structuredClone(valid);
    oneLockedSystem.locked_evaluations = { benzene: "not_run" };
    expect(() => validateRmd17DevelopmentSummary(oneLockedSystem)).toThrow(
      "locked_evaluations must contain exactly benzene, uracil",
    );
  });
});
