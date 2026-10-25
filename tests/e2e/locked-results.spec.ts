import { AxeBuilder } from "@axe-core/playwright";
import { expect, test } from "@playwright/test";

test("completed ChEMBL results retain every baseline and the failed assay transfer", async ({
  page,
}) => {
  await page.goto("/labs/chembl-egfr-representation-baselines/");
  const panel = page.getByRole("region", {
    name: "Completed ChEMBL evaluations",
    exact: true,
  });
  await expect(panel).toBeVisible();
  const primary = panel.getByRole("region", {
    name: "Primary scaffold test scores",
    exact: true,
  });
  const replication = panel.getByRole("region", {
    name: "Assay replication scores",
    exact: true,
  });
  for (const region of [primary, replication]) {
    await expect(region.getByRole("row")).toHaveCount(4);
    await expect(
      region.getByRole("rowheader", { name: "Train mean", exact: true }),
    ).toBeVisible();
    await expect(region.getByText("undefined", { exact: true })).toBeVisible();
  }
  await expect(
    primary.getByRole("row").filter({
      has: page.getByRole("rowheader", { name: "Morgan Ridge", exact: true }),
    }),
  ).toContainText("0.418330");
  await expect(
    replication.getByRole("row").filter({
      has: page.getByRole("rowheader", { name: "Morgan Ridge", exact: true }),
    }),
  ).toContainText("3.131676");
  await expect(panel).toContainText("T15 accessed labels shared with T05");
  await expect(
    page.getByRole("region", {
      name: "Selection evidence, not test performance",
    }),
  ).toContainText("MAE 0.373");
  await expect(
    panel.getByRole("link", {
      name: "Download all ChEMBL aggregate scores (JSON)",
    }),
  ).toHaveAttribute("href", /^data:application\/json/);
  expect((await new AxeBuilder({ page }).analyze()).violations).toEqual([]);
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= window.innerWidth,
    ),
  ).toBe(true);
});

test("completed rMD17 results show both systems and disclose the prediction evidence limit", async ({
  page,
}) => {
  await page.goto("/labs/rmd17-system-state-energy-baselines/");
  const panel = page.getByRole("region", {
    name: "Completed rMD17 evaluations",
    exact: true,
  });
  await expect(panel).toBeVisible();
  const scores = panel.getByRole("region", {
    name: "Completed rMD17 system scores",
    exact: true,
  });
  await expect(scores.getByRole("row")).toHaveCount(5);
  await expect(scores).toContainText("1.602273");
  await expect(scores).toContainText("3.123874");
  await expect(panel).toContainText("two molecular systems");
  await expect(panel).toContainText("not Ridge scores");
  await expect(
    page.getByRole("region", {
      name: "rMD17 development evidence",
      exact: true,
    }),
  ).toContainText("alpha 100");
  await expect(
    panel.getByRole("link", {
      name: "Download all rMD17 aggregate scores (JSON)",
    }),
  ).toHaveAttribute("href", /^data:application\/json/);
  expect((await new AxeBuilder({ page }).analyze()).violations).toEqual([]);
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= window.innerWidth,
    ),
  ).toBe(true);
});
