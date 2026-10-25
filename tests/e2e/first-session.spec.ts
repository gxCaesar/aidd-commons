import { readFile } from "node:fs/promises";
import { AxeBuilder } from "@axe-core/playwright";
import { expect, test } from "@playwright/test";
import { parse } from "yaml";

for (const route of ["/", "/zh-cn/"]) {
  test(`track cards link to existing introductions from ${route}`, async ({
    page,
    request,
  }) => {
    await page.goto(route);
    const links = page.locator("[data-track-summary] a");
    await expect(links).toHaveCount(18);
    const hrefs = await links.evaluateAll((elements) =>
      elements.map((element) => element.getAttribute("href")!),
    );
    expect(new Set(hrefs).size).toBe(18);
    for (const href of hrefs) {
      expect(
        href.startsWith(route === "/" ? "/learn/" : "/zh-cn/pathways/"),
      ).toBe(true);
      expect((await request.get(href)).ok()).toBe(true);
    }
  });
}

test("a new reader reaches the light lab and its completed predictive follow-up", async ({
  page,
}) => {
  await page.goto("/");
  await page.getByRole("link", { name: "Choose a pathway" }).click();
  await page
    .getByRole("link", { name: "Your first session", exact: true })
    .click();
  await expect(
    page.getByRole("heading", { name: "Your first session", exact: true }),
  ).toBeVisible();
  await expect(
    page.getByText("tmp/molecule-representations/report.json", { exact: true }),
  ).toBeVisible();
  expect((await new AxeBuilder({ page }).analyze()).violations).toEqual([]);
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
  ).toBe(true);
  await page
    .getByRole("link", { name: "Run the label-free inspector", exact: true })
    .click();
  await expect(
    page.getByRole("heading", { name: "Expected relationships", exact: true }),
  ).toBeVisible();
  await page
    .getByRole("link", {
      name: "Read the completed ChEMBL comparison",
      exact: true,
    })
    .click();
  await expect(
    page.getByRole("region", {
      name: "Completed ChEMBL evaluations",
      exact: true,
    }),
  ).toBeVisible();
});

test("report readers can read the current addendum and retrieve the unmodified historical PDF", async ({
  page,
  request,
}) => {
  await page.goto("/report/");
  const pdfLink = page.getByRole("link", {
    name: "Download historical v0.1 PDF",
    exact: true,
  });
  const pdfResponse = await request.get((await pdfLink.getAttribute("href"))!);
  expect(pdfResponse.ok()).toBe(true);
  expect(await pdfResponse.body()).toEqual(
    await readFile("site/public/reports/aidd-commons-living-report-v0.1.pdf"),
  );
  const citationResponse = await request.get(
    (await page
      .getByRole("link", { name: "Download version citation", exact: true })
      .getAttribute("href"))!,
  );
  expect(citationResponse.ok()).toBe(true);
  const citation = parse(await citationResponse.text());
  const manifest = JSON.parse(await readFile("package.json", "utf8"));
  expect(citation.version).toBe(manifest.version);
  await page
    .getByRole("link", { name: "Read the v0.2 addendum", exact: true })
    .click();
  await expect(
    page.getByRole("heading", {
      name: "What the completed labs establish",
      exact: true,
    }),
  ).toBeVisible();
  expect((await new AxeBuilder({ page }).analyze()).violations).toEqual([]);
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
  ).toBe(true);
});
