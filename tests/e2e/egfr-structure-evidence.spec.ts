import { AxeBuilder } from "@axe-core/playwright";
import { expect, test } from "@playwright/test";

const editions = [
  { path: "/labs/egfr-structure-evidence/", index: "/labs/" },
  { path: "/zh-cn/labs/egfr-structure-evidence/", index: "/zh-cn/labs/" },
];

for (const { path, index } of editions) {
  test(`${path} offers every file the commands need and keeps its answers folded`, async ({
    page,
  }) => {
    await page.goto(index);
    await expect(page.locator(`main a[href="${path}"]`).first()).toBeVisible();

    await page.goto(path);
    const downloads = page.locator("[data-lab-downloads] a");
    await expect(downloads).toHaveCount(7);
    for (const file of [
      "cif.py",
      "inspect_state.py",
      "inspect_complex.py",
      "entries.json",
      "structures/1M17.cif",
      "structures/4HJO.cif",
      "structures/1XKK.cif",
    ]) {
      await expect(
        page.locator(
          `[data-lab-downloads] a[href="/downloads/labs/egfr_structures/${file}"]`,
        ),
      ).toHaveCount(1);
    }

    // Both exercises keep their worked answers closed until the reader opens them.
    const answers = page.locator("details[data-worked-answer]");
    await expect(answers).toHaveCount(2);
    for (const answer of await answers.all()) {
      await expect(answer).not.toHaveAttribute("open", /.*/);
    }

    // The constructed poses are printed as terminal output in both editions,
    // and must never lose their label.
    await expect(
      page
        .locator("main pre")
        .filter({
          hasText: "constructed: translated 1.5 A away from the hinge",
        }),
    ).toHaveCount(1);

    const results = await new AxeBuilder({ page }).analyze();
    const blocking = results.violations.filter((violation) =>
      ["serious", "critical"].includes(violation.impact ?? ""),
    );
    expect(blocking).toEqual([]);
  });
}
