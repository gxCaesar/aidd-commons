import { readFile } from "node:fs/promises";
import { AxeBuilder } from "@axe-core/playwright";
import { expect, test } from "@playwright/test";

test("notebook-first entry offers exact bilingual downloads and honest Colab upload", async ({
  page,
  request,
}, testInfo) => {
  for (const prefix of ["", "/zh-cn"]) {
    await page.goto(`${prefix}/labs/`);
    await page
      .locator(`a[href="${prefix}/labs/lipophilicity-notebook/"]`)
      .click();
    await expect(page).toHaveURL(
      new RegExp(`${prefix}/labs/lipophilicity-notebook/`),
    );
    await expect(page.getByRole("heading", { level: 1 })).toBeVisible();
    const colab = page.locator(
      'main a[href="https://colab.research.google.com/"]',
    );
    await expect(colab).toBeVisible();
    await expect(page.locator("main")).toContainText("Upload notebook");
    await expect(page.locator("[data-lab-downloads]")).toContainText(
      prefix ? "自包含" : "self-contained",
    );
    for (const suffix of ["", ".zh-CN"]) {
      const path = `labs/lipophilicity/lipophilicity_tutorial${suffix}.ipynb`;
      await expect(
        page.locator(`[data-lab-downloads] a[href="/downloads/${path}"]`),
      ).toBeVisible();
      const response = await request.get(`/downloads/${path}`);
      expect(response.status()).toBe(200);
      expect(await response.text()).toBe(await readFile(path, "utf8"));
      const notebook = JSON.parse(await response.text());
      expect(
        notebook.cells.filter(
          (cell: { cell_type: string }) => cell.cell_type === "code",
        ).length,
      ).toBeGreaterThan(10);
    }
    expect(
      await page.evaluate(
        () => document.documentElement.scrollWidth <= window.innerWidth + 1,
      ),
    ).toBe(true);
    const code = page.locator("pre").first();
    if (
      await code.evaluate(
        (element) => element.scrollWidth > element.clientWidth,
      )
    ) {
      await expect(code).toHaveAttribute("tabindex", "0");
      await code.focus();
      await expect(code).toBeFocused();
    }
    await page.screenshot({
      path: testInfo.outputPath(prefix ? "chinese.png" : "english.png"),
    });
    const accessibility = await new AxeBuilder({ page }).analyze();
    expect(
      accessibility.violations.filter((item) =>
        ["critical", "serious"].includes(item.impact ?? ""),
      ),
    ).toEqual([]);
  }
  expect(
    (
      await request.get("/downloads/labs/lipophilicity/Lipophilicity.csv")
    ).status(),
  ).toBe(404);
  expect(
    (await request.get("/downloads/labs/lipophilicity/summary.json")).status(),
  ).toBe(404);
});
