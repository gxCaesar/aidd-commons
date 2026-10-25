import { AxeBuilder } from "@axe-core/playwright";
import { expect, test } from "@playwright/test";

for (const prefix of ["", "/zh-cn"]) {
  test(`lesson routes continue in the declared order in ${prefix || "English"}`, async ({
    page,
  }, testInfo) => {
    if (testInfo.project.name === "mobile-chromium") {
      await page.setViewportSize({ width: 320, height: 900 });
    }
    await page.goto(`${prefix}/learn/foundations/first-session/`);
    const core = page.locator(
      '[data-lesson-navigation] [data-lesson-route="core"]',
    );
    await expect(core.locator("[data-previous-lesson]")).toHaveAttribute(
      "href",
      `${prefix}/learn/foundations/getting-started/`,
    );
    await core.locator("[data-next-lesson]").click();
    await expect(page).toHaveURL(
      new RegExp(`${prefix}/learn/foundations/source-and-entity-literacy/$`),
    );
    await page
      .locator('[data-lesson-route="core"] [data-previous-lesson]')
      .click();
    await expect(page).toHaveURL(
      new RegExp(`${prefix}/learn/foundations/first-session/$`),
    );

    await page.goto(
      `${prefix}/learn/structure-and-pockets/cofolding-frontier/`,
    );
    await expect(
      page.locator("[data-lesson-navigation] [data-lesson-route]"),
    ).toHaveCount(3);
    await expect(
      page.locator('[data-lesson-route="core"] [data-next-lesson]'),
    ).toHaveAttribute(
      "href",
      `${prefix}/learn/physics-based-modeling/docking-to-fep/`,
    );
    await expect(
      page.locator(
        '[data-lesson-route="structure-physics"] [data-next-lesson]',
      ),
    ).toHaveAttribute(
      "href",
      `${prefix}/learn/structure-and-pockets/structure-affinity-mechanisms/`,
    );
    await page
      .locator("[data-lesson-navigation]")
      .screenshot({ path: testInfo.outputPath("branching-navigation.png") });
    await page.locator('[data-lesson-route="structure-physics"] h3 a').click();
    await expect(
      page.locator("#learning-route-structure-physics"),
    ).toBeInViewport();

    await page.goto(`${prefix}/learn/candidate-nomination/capstone/`);
    await expect(
      page.locator('[data-lesson-route="core"] [data-next-lesson]'),
    ).toHaveCount(0);
    await expect(page.locator('[data-lesson-route="core"]')).toContainText(
      prefix ? "已到本路径末尾" : "end of this route",
    );
    await expect(
      page.locator('[data-lesson-route="small-molecules"] [data-next-lesson]'),
    ).toHaveAttribute(
      "href",
      `${prefix}/learn/candidate-nomination/evidence-to-validation/`,
    );
    await page
      .locator("[data-lesson-navigation]")
      .screenshot({ path: testInfo.outputPath("route-end-navigation.png") });

    await page.goto(
      `${prefix}/learn/foundations/source-review-and-claim-scope/`,
    );
    await expect(
      page.locator('[data-lesson-route="foundations"]'),
    ).toContainText(prefix ? "本专题内" : "Within this track");
    await page.locator('[data-lesson-route="foundations"] h3 a').click();
    await expect(page.locator("#track-foundations")).toBeInViewport();
    await page.goBack();
    expect(
      await page.evaluate(
        () => document.documentElement.scrollWidth <= innerWidth + 1,
      ),
    ).toBe(true);
    const audit = await new AxeBuilder({ page })
      .include("[data-lesson-navigation]")
      .analyze();
    expect(
      audit.violations.filter(
        ({ impact }) => impact === "serious" || impact === "critical",
      ),
    ).toEqual([]);
    for (const link of await page.locator("[data-lesson-navigation] a").all()) {
      expect((await link.boundingBox())!.height).toBeGreaterThanOrEqual(44);
    }
  });
}

test.describe("lesson continuation without JavaScript", () => {
  test.use({ javaScriptEnabled: false });
  for (const prefix of ["", "/zh-cn"]) {
    test(`server-rendered links work in ${prefix || "English"}`, async ({
      page,
    }) => {
      await page.goto(`${prefix}/learn/foundations/first-session/`);
      await page
        .locator('[data-lesson-route="core"] [data-next-lesson]')
        .click();
      await expect(page).toHaveURL(
        new RegExp(`${prefix}/learn/foundations/source-and-entity-literacy/$`),
      );
    });
  }
});
