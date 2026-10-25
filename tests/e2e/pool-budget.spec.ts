import { AxeBuilder } from "@axe-core/playwright";
import { expect, test } from "@playwright/test";

test("pool lesson calculates equal budgets without changing observed curves", async ({
  page,
}, testInfo) => {
  await page.setViewportSize(
    testInfo.project.name === "mobile-chromium"
      ? { width: 375, height: 812 }
      : { width: 1365, height: 900 },
  );
  await page.goto("/learn/active-learning/experiment-pools-and-budgets/");
  await expect(page.getByRole("heading", { level: 1 })).toHaveText(
    "Experiment pools, budgets, and feasibility",
  );
  const input = page.getByLabel("Original candidate pool size");
  await input.fill("631");
  await expect(page.locator("#budget-output")).toContainText(
    "31 per round · 124 labels total",
  );
  await expect(
    page.getByText("Observed synthetic top-decile recovery", { exact: false }),
  ).toContainText("original pool = 42");
  await input.fill("19");
  await expect(input).toHaveAttribute("aria-invalid", "true");
  await input.fill("42");
  await expect(page.locator("#budget-output")).toContainText("8 labels total");
  expect((await new AxeBuilder({ page }).analyze()).violations).toEqual([]);
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= window.innerWidth,
    ),
  ).toBe(true);
  await page.goto("/labs/pool-budget-campaign/");
  await expect(page.getByRole("heading", { level: 1 })).toHaveText(
    "Pool-budget campaign simulator",
  );
});

test("real pool results retain every policy and separate the synthetic calculator", async ({
  page,
}) => {
  await page.goto("/labs/pool-budget-campaign/");
  await expect(
    page.getByRole("heading", {
      name: "Real ChEMBL campaign results",
      exact: true,
    }),
  ).toBeVisible();
  const primary = page.getByRole("region", {
    name: "CHEMBL5736995 final campaign scores",
    exact: true,
  });
  const external = page.getByRole("region", {
    name: "CHEMBL3705421 final campaign scores",
    exact: true,
  });
  for (const region of [primary, external]) {
    await expect(region.getByRole("row")).toHaveCount(7);
    await expect(
      region.getByRole("rowheader", { name: "random-4", exact: true }),
    ).toBeVisible();
  }
  await expect(
    primary.getByRole("row").filter({
      has: page.getByRole("rowheader", { name: "maxmin", exact: true }),
    }),
  ).toContainText("0.05078125");
  await expect(
    external.getByRole("row").filter({
      has: page.getByRole("rowheader", { name: "maxmin", exact: true }),
    }),
  ).toContainText("0.00000000");
  await expect(
    page.getByText("Its original pool contains one scaffold group", {
      exact: false,
    }),
  ).toBeVisible();
  const original = await primary.innerText();
  await page.getByLabel("Original candidate pool size").fill("100");
  expect(await primary.innerText()).toBe(original);
  await page
    .getByText("All checkpoints for CHEMBL5736995", { exact: true })
    .click();
  await expect(
    page
      .getByRole("region", {
        name: "CHEMBL5736995 all checkpoint scores",
        exact: true,
      })
      .getByRole("row"),
  ).toHaveCount(31);
  expect((await new AxeBuilder({ page }).analyze()).violations).toEqual([]);
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= window.innerWidth,
    ),
  ).toBe(true);
});
