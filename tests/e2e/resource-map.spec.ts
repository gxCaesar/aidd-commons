import { readFile } from "node:fs/promises";
import { AxeBuilder } from "@axe-core/playwright";
import { expect, test } from "@playwright/test";
import { parse } from "yaml";

const curriculum = parse(
  await readFile("catalog/curriculum/tracks.yaml", "utf8"),
);

for (const prefix of ["", "/zh-cn"]) {
  test(`agent resource guide connects the map to tools and benchmarks in ${prefix || "English"}`, async ({
    page,
  }) => {
    await page.goto(`${prefix}/learn/foundations/resource-map/`);
    await page
      .locator(
        `main a[href="${prefix}/learn/scientific-agents/agent-resource-guide/"]`,
      )
      .click();
    await expect(page.locator("lesson-progress")).toHaveAttribute(
      "data-lesson-id",
      "scientific-agents/agent-resource-guide",
    );
    for (const [id, url] of [
      ["agent-paperqa", "https://github.com/Future-House/paper-qa"],
      ["benchmark-lab-bench", "https://github.com/Future-House/LAB-Bench"],
      ["benchmark-bixbench", "https://github.com/Future-House/BixBench"],
    ]) {
      await page.locator(`main table a[href="/atlas/${id}/"]`).click();
      await expect(page.locator(`main a[href="${url}"]`).first()).toBeVisible();
      await page.goBack();
    }
  });

  test(`current resource map preserves unit scope and reaches teaching in ${prefix || "English"}`, async ({
    page,
    request,
  }, testInfo) => {
    await page.goto(`${prefix}/learn/foundations/curriculum-map/`);
    await page
      .locator(`main a[href="${prefix}/learn/foundations/resource-map/"]`)
      .click();
    await expect(page.locator("[data-resource-unit]")).toHaveCount(
      curriculum.units.length,
    );
    const response = await request.get("/data/curriculum-resources.json");
    expect(response.status()).toBe(200);
    const data = await response.json();
    expect(data.rows).toHaveLength(curriculum.units.length);
    for (const unit of curriculum.units) {
      const row = data.rows.find(
        (entry: { unit_id: string }) => entry.unit_id === unit.id,
      );
      expect(row.lesson_id).toBe(unit.lesson_id ?? null);
      expect(row.unit_resource_sufficiency).toBe("not_assessed");
      if (unit.lesson_id) {
        await expect(
          page.locator(
            `[data-resource-unit="${unit.id}"] [data-resource-lesson]`,
          ),
        ).toHaveAttribute("href", `${prefix}/learn/${unit.lesson_id}/`);
      }
    }
    const track = page.locator('[data-resource-track="mechanism-targets"]');
    await track.locator(":scope > summary").focus();
    await page.keyboard.press("Enter");
    await expect(track).toHaveAttribute("open", "");
    expect(
      await page.evaluate(
        () => document.documentElement.scrollWidth <= innerWidth + 1,
      ),
    ).toBe(true);
    const audit = await new AxeBuilder({ page }).analyze();
    expect(
      audit.violations.filter(
        ({ impact }) => impact === "serious" || impact === "critical",
      ),
    ).toEqual([]);
    await page.screenshot({
      path: testInfo.outputPath("resource-map.png"),
      fullPage: true,
    });
    await page
      .locator(
        `main a[href="${prefix}/learn/mechanism-targets/target-resource-guide/"]`,
      )
      .first()
      .click();
    await expect(page.locator("lesson-progress")).toHaveAttribute(
      "data-lesson-id",
      "mechanism-targets/target-resource-guide",
    );
  });
}

test("Atlas resources link back to their registered teaching use", async ({
  page,
}) => {
  await page.goto("/atlas/db-open-targets-platform/");
  await page
    .locator(
      '[data-resource-learning] a[href="/learn/mechanism-targets/target-resource-guide/"]',
    )
    .click();
  await expect(page.locator("lesson-progress")).toHaveAttribute(
    "data-lesson-id",
    "mechanism-targets/target-resource-guide",
  );
});
