import { readFile } from "node:fs/promises";
import { AxeBuilder } from "@axe-core/playwright";
import { expect, test } from "@playwright/test";

test("bilingual notebook route reaches runnable downloads and keeps result reading separate", async ({
  page,
  request,
}, testInfo) => {
  for (const prefix of ["", "/zh-cn"]) {
    await page.goto(`${prefix}/labs/`);
    await page.locator(`a[href="${prefix}/labs/notebook-guide/"]`).click();
    await expect(page.getByRole("heading", { level: 1 })).toBeVisible();
    const routes = [
      {
        href: "/labs/molecule-representation-inspector/",
        base: "labs/molecule_representations/representation_inspector",
      },
      {
        href: "/learn/machine-learning/student-modelling-sandbox/",
        base: "labs/student_modelling/student_modelling_tutorial",
      },
      {
        href: "/labs/lipophilicity-notebook/",
        base: "labs/lipophilicity/lipophilicity_tutorial",
      },
      {
        href: "/learn/scientific-agents/agent-resource-guide/",
        base: "labs/paperqa_local/paperqa_local_tutorial",
      },
    ];
    const guide = `${prefix}/labs/notebook-guide/`;
    for (const route of routes) {
      await page
        .locator(`main a[href="${prefix}${route.href}"]`)
        .first()
        .click();
      await expect(page.getByRole("heading", { level: 1 })).toBeVisible();
      for (const suffix of ["", ".zh-CN"]) {
        const path = `${route.base}${suffix}.ipynb`;
        await expect(
          page.locator(`main a[href="/downloads/${path}"]`),
        ).toBeVisible();
        const response = await request.get(`/downloads/${path}`);
        expect(response.status()).toBe(200);
        expect(await response.text()).toBe(await readFile(path, "utf8"));
        const book = JSON.parse(await response.text());
        expect(
          book.cells.filter(
            (cell: { cell_type: string }) => cell.cell_type === "code",
          ).length,
        ).toBeGreaterThan(4);
        expect(
          book.cells.some(
            (cell: { outputs?: unknown[] }) => cell.outputs?.length,
          ),
        ).toBe(false);
      }
      await page.goto(guide);
    }
    await expect(
      page.locator(`main a[href="${prefix}/labs/freesolv-honest-baselines/"]`),
    ).toBeVisible();
    await expect(
      page.locator('main a[href="https://colab.research.google.com/"]'),
    ).toBeVisible();
    expect(
      await page.evaluate(
        () => document.documentElement.scrollWidth <= window.innerWidth + 1,
      ),
    ).toBe(true);
    for (const table of await page
      .locator(".sl-markdown-content table")
      .all()) {
      if (
        await table.evaluate(
          (element) => element.scrollWidth > element.clientWidth,
        )
      ) {
        await expect(table).toHaveAttribute("tabindex", "0");
      }
    }
    if ((page.viewportSize()?.width ?? 1280) < 600) {
      const routeTable = page.locator(".sl-markdown-content table").first();
      expect(
        await routeTable.evaluate(
          (element) => element.scrollWidth > element.clientWidth,
        ),
      ).toBe(true);
      await routeTable.focus();
      await expect(routeTable).toBeFocused();
    }
    const accessibility = await new AxeBuilder({ page }).analyze();
    expect(
      accessibility.violations.filter((item) =>
        ["critical", "serious"].includes(item.impact ?? ""),
      ),
    ).toEqual([]);
    await page.screenshot({
      path: testInfo.outputPath(
        prefix ? "guide-chinese.png" : "guide-english.png",
      ),
    });
  }
  for (const path of [
    "labs/student_modelling/executed.ipynb",
    "labs/molecule_representations/student-report.json",
  ]) {
    expect((await request.get(`/downloads/${path}`)).status()).toBe(404);
  }
});
