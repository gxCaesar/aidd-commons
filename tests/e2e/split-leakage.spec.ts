import { AxeBuilder } from "@axe-core/playwright";
import { expect, test } from "@playwright/test";

const lessons = [
  {
    id: "split-and-leakage-cases",
    track: "/learn/evaluation-and-reproducibility/",
    entryId: "honest-evaluation",
    sourceCount: 3,
  },
  {
    id: "metrics-and-uncertainty",
    track: "/learn/evaluation-and-reproducibility/",
    entryId: "honest-evaluation",
    sourceCount: 4,
  },
  {
    id: "diversity-uncertainty-feedback",
    track: "/learn/active-learning/",
    entryId: "dmta-loops",
    sourceCount: 2,
  },
];

for (const { id, track, entryId, sourceCount } of lessons) {
  const lesson = `${track}${id}/`;

  for (const prefix of ["", "/zh-cn"]) {
    test(`${id}: readers can reach and inspect the cross-lab exercise in ${prefix || "English"}`, async ({
      page,
      request,
    }) => {
      await page.goto(`${prefix}${track}${entryId}/`);
      const entry = page.locator(`main a[href="${prefix}${lesson}"]`);
      await expect(entry).toBeVisible();
      await entry.click();
      await expect(page).toHaveURL(`${prefix}${lesson}`);

      const answers = page.locator("details[data-worked-answer]");
      await expect(answers).toHaveCount(4);
      for (const answer of await answers.all()) {
        expect(await answer.getAttribute("open")).toBeNull();
        const summary = answer.locator("summary");
        await summary.focus();
        await page.keyboard.press("Enter");
        await expect(answer).toHaveAttribute("open", "");
        await expect(answer.locator("p").first()).toBeVisible();
      }

      const sources = page.locator("[data-case-sources] a");
      const hrefs = await sources.evaluateAll((links) =>
        links.map((link) => link.getAttribute("href")!),
      );
      expect(hrefs).toHaveLength(sourceCount);
      for (const href of hrefs) {
        expect(href.startsWith(`${prefix}/labs/`)).toBe(true);
        expect((await request.get(href)).ok(), href).toBe(true);
      }
      await sources.first().click();
      await expect(page.getByRole("heading", { level: 1 })).toContainText(
        "ChEMBL",
      );
    });

    test(`${id}: the cross-lab exercise stays readable at narrow widths in ${prefix || "English"}`, async ({
      page,
    }) => {
      await page.setViewportSize({ width: 320, height: 850 });
      expect((await page.goto(`${prefix}${lesson}`))?.status()).toBe(200);
      for (const summary of await page
        .locator("details[data-worked-answer] summary")
        .all())
        await summary.click();
      expect(
        await page.evaluate(
          () => document.documentElement.scrollWidth <= innerWidth,
        ),
      ).toBe(true);
      const audit = await new AxeBuilder({ page }).analyze();
      expect(
        audit.violations.filter(
          ({ impact }) => impact === "critical" || impact === "serious",
        ),
      ).toEqual([]);
    });
  }

  test(`${id}: the exercise shares progress with its canonical English lesson`, async ({
    page,
  }) => {
    await page.goto(`/zh-cn${lesson}`);
    await page.getByRole("button", { name: "标记本课完成" }).click();
    await page.locator(`main a[href="${lesson}"]`).click();
    await expect(
      page.getByRole("button", { name: "Mark lesson complete" }),
    ).toHaveAttribute("aria-pressed", "true");
    await page.reload();
    await expect(page.locator("[data-progress-status]")).toHaveText(
      "Completed",
    );
  });
}
