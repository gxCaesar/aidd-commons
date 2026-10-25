import { AxeBuilder } from "@axe-core/playwright";
import { expect, test } from "@playwright/test";

test("representation lesson exposes its decision map and executable lab", async ({
  page,
}, testInfo) => {
  if (testInfo.project.name === "mobile-chromium") {
    await page.setViewportSize({ width: 320, height: 720 });
  }

  await page.goto("/learn/representations/small-molecule-representations/");

  await expect(
    page.getByRole("heading", {
      level: 1,
      name: "Small-molecule representations",
    }),
  ).toBeVisible();
  await expect(
    page.getByRole("heading", {
      name: "Representation is a chain of scientific choices",
    }),
  ).toBeVisible();
  await expect(page.locator("[data-representation-map]")).toBeVisible();
  await expect(
    page.getByRole("link", { name: "label-free representation inspector" }),
  ).toHaveAttribute("href", "/labs/molecule-representation-inspector/");

  const pageWidth = await page.evaluate(() => ({
    client: document.documentElement.clientWidth,
    scroll: document.documentElement.scrollWidth,
  }));
  expect(pageWidth.scroll).toBeLessThanOrEqual(pageWidth.client);

  await page.goto("/labs/molecule-representation-inspector/");
  await expect(
    page.getByRole("heading", {
      level: 1,
      name: "Label-free molecule representation inspector",
    }),
  ).toBeVisible();
  await expect(
    page.getByRole("heading", { name: "Input and output contract" }),
  ).toBeVisible();
  await expect(
    page.getByText("It does not load activity labels", { exact: false }),
  ).toBeVisible();

  await page.goto("/audit/");
  const candidate = page.locator(".candidate-card").filter({
    has: page.getByRole("heading", { name: "Small-molecule representations" }),
  });
  await expect(candidate.getByText("Completed", { exact: true })).toBeVisible();
});

test("representation lesson has no serious or critical accessibility violations", async ({
  page,
}) => {
  await page.goto("/learn/representations/small-molecule-representations/");

  const results = await new AxeBuilder({ page }).analyze();
  const blockingViolations = results.violations.filter((violation) =>
    ["serious", "critical"].includes(violation.impact ?? ""),
  );
  expect(blockingViolations).toEqual([]);
});

test("ChEMBL EGFR lab keeps development evidence separate from locked evaluation", async ({
  page,
}, testInfo) => {
  if (testInfo.project.name === "mobile-chromium") {
    await page.setViewportSize({ width: 320, height: 720 });
  }

  await page.goto("/labs/chembl-egfr-representation-baselines/");

  await expect(
    page.getByRole("heading", {
      level: 1,
      name: "ChEMBL 37 EGFR representation baselines",
    }),
  ).toBeVisible();
  await expect(
    page.getByRole("region", {
      name: "Selection evidence, not test performance",
    }),
  ).toContainText("MAE 0.373");
  const lockRegion = page.getByRole("region", {
    name: "Status at the development freeze",
  });
  await expect(lockRegion.getByText("not_run", { exact: true })).toHaveCount(2);

  const pageWidth = await page.evaluate(() => ({
    client: document.documentElement.clientWidth,
    scroll: document.documentElement.scrollWidth,
  }));
  expect(pageWidth.scroll).toBeLessThanOrEqual(pageWidth.client);

  const results = await new AxeBuilder({ page }).analyze();
  const blockingViolations = results.violations.filter((violation) =>
    ["serious", "critical"].includes(violation.impact ?? ""),
  );
  expect(blockingViolations).toEqual([]);
});
