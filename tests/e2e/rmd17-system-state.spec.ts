import { AxeBuilder } from "@axe-core/playwright";
import { expect, test } from "@playwright/test";

const labRoute = "/labs/rmd17-system-state-energy-baselines/";

test("rMD17 development lab keeps its public evidence readable at desktop and 375 px", async ({
  page,
}, testInfo) => {
  await page.setViewportSize(
    testInfo.project.name === "mobile-chromium"
      ? { width: 375, height: 812 }
      : { width: 1365, height: 900 },
  );
  await page.goto(labRoute);

  await expect(
    page.getByRole("heading", {
      level: 1,
      name: "rMD17 system-state energy baselines",
    }),
  ).toBeVisible();
  const panel = page.getByRole("region", {
    name: "rMD17 development evidence",
  });
  await expect(panel).toContainText("Development pretest passed");
  await expect(panel).toContainText("ethanol");
  await expect(panel).toContainText("malonaldehyde");
  await expect(panel).toContainText("benzene");
  await expect(panel).toContainText("uracil");
  await expect(
    panel
      .getByRole("list", { name: "Locked statuses at development freeze" })
      .getByText("not_run", { exact: true }),
  ).toHaveCount(2);
  await expect(
    page.getByRole("heading", {
      name: "Development observations and limits",
    }),
  ).toBeVisible();

  const pageWidth = await page.evaluate(() => ({
    client: document.documentElement.clientWidth,
    scroll: document.documentElement.scrollWidth,
  }));
  expect(pageWidth.scroll).toBeLessThanOrEqual(pageWidth.client);

  await page.goto("/labs/");
  await expect(
    page.getByRole("link", { name: "Study the rMD17 evidence" }),
  ).toHaveAttribute("href", labRoute);
  await expect(
    page.getByText("Benzene and uracil evaluations completed", {
      exact: false,
    }),
  ).toBeVisible();
});

test("rMD17 development lab has no serious or critical accessibility violations", async ({
  page,
}) => {
  await page.goto(labRoute);
  await expect(
    page.getByRole("heading", {
      level: 1,
      name: "rMD17 system-state energy baselines",
    }),
  ).toBeVisible();

  const results = await new AxeBuilder({ page }).analyze();
  const blockingViolations = results.violations.filter((violation) =>
    ["serious", "critical"].includes(violation.impact ?? ""),
  );
  expect(blockingViolations).toEqual([]);
});
