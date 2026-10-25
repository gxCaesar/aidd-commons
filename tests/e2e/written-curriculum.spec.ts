import { readFile } from "node:fs/promises";
import { AxeBuilder } from "@axe-core/playwright";
import { expect, test } from "@playwright/test";
import { parse } from "yaml";

const curriculum = parse(
  await readFile(
    new URL("../../catalog/curriculum/tracks.yaml", import.meta.url),
    "utf8",
  ),
) as {
  tracks: Array<{
    id: string;
    lessons: Array<{ id: string; capabilities?: string[] }>;
  }>;
};

// A chapter advertised as a written exercise must expose its answer and remain
// usable after that answer is expanded. Scope follows the delivered catalog.
for (const track of curriculum.tracks) {
  const lessons = track.lessons.filter(
    ({ capabilities }) =>
      capabilities?.includes("exercise") && !capabilities.includes("runnable"),
  );
  if (lessons.length === 0) continue;
  for (const prefix of ["", "/zh-cn"]) {
    test(`${track.id} written exercises work in ${prefix || "English"}`, async ({
      page,
    }, testInfo) => {
      for (const lesson of lessons) {
        const id = `${track.id}/${lesson.id}`;
        expect((await page.goto(`${prefix}/learn/${id}/`))?.status()).toBe(200);
        await expect(page.locator("lesson-progress")).toHaveAttribute(
          "data-lesson-id",
          id,
        );
        const answers = page.locator("details[data-worked-answer]");
        expect(await answers.count(), id).toBeGreaterThan(0);
        for (const answer of await answers.all()) {
          await expect(answer).not.toHaveAttribute("open", "");
          await answer.locator("summary").focus();
          await page.keyboard.press("Enter");
          await expect(answer).toHaveAttribute("open", "");
          await expect(
            answer.locator("p, table, ul, ol").first(),
          ).toBeVisible();
        }
        expect(
          await page.evaluate(
            () => document.documentElement.scrollWidth <= innerWidth + 1,
          ),
          id,
        ).toBe(true);
        if (
          [
            "physics-resource-guide",
            "generation-resource-guide",
            "agent-resource-guide",
          ].includes(lesson.id)
        ) {
          const table = page.locator("main table").first();
          const columns = await table
            .locator("th")
            .evaluateAll((cells) =>
              cells.map((cell) => cell.getBoundingClientRect().width),
            );
          expect(
            Math.min(...columns),
            `${id}: readable table columns`,
          ).toBeGreaterThanOrEqual(120);
          if (
            await table.evaluate(
              (element) => element.scrollWidth > element.clientWidth,
            )
          ) {
            await expect(table).toHaveAttribute("tabindex", "0");
            await table.focus();
            await page.keyboard.press("ArrowRight");
            await expect
              .poll(() => table.evaluate((element) => element.scrollLeft))
              .toBeGreaterThan(0);
          }
        }
        const audit = await new AxeBuilder({ page }).analyze();
        expect(
          audit.violations.filter(
            ({ impact }) => impact === "critical" || impact === "serious",
          ),
          id,
        ).toEqual([]);
        if (lesson.id === "capstone-workbook") {
          await page.screenshot({
            path: testInfo.outputPath("capstone.png"),
            fullPage: true,
          });
        }
      }
    });
  }
}
