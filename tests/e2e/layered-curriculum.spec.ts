import { readFile } from "node:fs/promises";
import { AxeBuilder } from "@axe-core/playwright";
import { expect, test } from "@playwright/test";
import { parse } from "yaml";

const curriculum = parse(
  await readFile(
    new URL("../../catalog/curriculum/tracks.yaml", import.meta.url),
    "utf8",
  ),
) as { units: Array<{ id: string; lesson_id?: string }> };

const map = "/learn/foundations/curriculum-map/";
const modellingLine = [
  "data-governance/records-to-model-table",
  "machine-learning/baseline-training-validation",
  "qsar-properties/regression-classification-errors",
  "machine-learning/student-modelling-sandbox",
];
const mechanismLessons = [
  "structure-and-pockets/structure-affinity-mechanisms",
  "molecular-generation/generative-model-mechanisms",
  "mechanism-targets/perturbation-context-generalization",
  "scientific-agents/retrieval-tools-feedback",
];

for (const prefix of ["", "/zh-cn"]) {
  test(`research decision cases are reachable and reveal worked answers in ${prefix || "English"}`, async ({
    page,
  }) => {
    for (const [route, lessonId] of [
      [
        "small-molecules",
        "evaluation-and-reproducibility/assay-shift-diagnosis",
      ],
      ["targets-cells", "candidate-nomination/evidence-to-validation"],
    ]) {
      await page.goto(`${prefix}${map}`);
      await page
        .locator(
          `[data-learning-path="${route}"] a[href="${prefix}/learn/${lessonId}/"]`,
        )
        .first()
        .click();
      await expect(page.locator("lesson-progress")).toHaveAttribute(
        "data-lesson-id",
        lessonId,
      );
      const answer = page.locator("details[data-worked-answer]").first();
      await expect(answer).not.toHaveAttribute("open", "");
      await answer.locator("summary").focus();
      await page.keyboard.press("Enter");
      await expect(answer).toHaveAttribute("open", "");
      await expect(answer.locator("p").first()).toBeVisible();
    }
  });

  test(`biological evidence chapters are reachable from their specialist routes in ${prefix || "English"}`, async ({
    page,
  }) => {
    for (const [route, lessonId] of [
      [
        "small-molecules",
        "drug-discovery-foundations/assay-controls-dose-response",
      ],
      ["targets-cells", "mechanism-targets/genetics-to-target-evidence"],
      ["small-molecules", "admet-pk/exposure-clearance-pkpd"],
    ]) {
      await page.goto(`${prefix}${map}`);
      await page
        .locator(
          `[data-learning-path="${route}"] a[href="${prefix}/learn/${lessonId}/"]`,
        )
        .first()
        .click();
      await expect(page.locator("lesson-progress")).toHaveAttribute(
        "data-lesson-id",
        lessonId,
      );
      const answer = page.locator("details[data-worked-answer]").first();
      await expect(answer).not.toHaveAttribute("open", "");
      await answer.locator("summary").focus();
      await page.keyboard.press("Enter");
      await expect(answer).toHaveAttribute("open", "");
      await expect(answer.locator("p").first()).toBeVisible();
    }
  });

  test(`the curriculum exposes ordered lessons without linking planned pages in ${prefix || "English"}`, async ({
    page,
    request,
  }) => {
    const response = await page.goto(`${prefix}${map}`);
    expect(response?.status()).toBe(200);
    const core = page.locator('[data-learning-path="core"]');
    await expect(core).toBeVisible();
    await expect(page.locator("[data-learning-path]")).toHaveCount(6);
    const links = await core
      .locator("a")
      .evaluateAll((anchors) =>
        anchors.map((anchor) => anchor.getAttribute("href")),
      );
    const positions = modellingLine.map((id) =>
      links.indexOf(`${prefix}/learn/${id}/`),
    );
    expect(positions.every((position) => position >= 0)).toBe(true);
    expect(positions).toEqual([...positions].sort((a, b) => a - b));
    const planned = page.locator(
      '[data-curriculum-unit][data-unit-state="planned"]',
    );
    await expect(planned).toHaveCount(
      curriculum.units.filter((unit) => !unit.lesson_id).length,
    );
    await expect(planned.locator("[data-unit-lesson]")).toHaveCount(0);
    await expect(page.locator("[data-curriculum-unit]")).toHaveCount(
      curriculum.units.length,
    );
    for (const unit of curriculum.units.filter((unit) => unit.lesson_id)) {
      await expect(
        page.locator(`[data-curriculum-unit="${unit.id}"] [data-unit-lesson]`),
      ).toHaveAttribute("href", `${prefix}/learn/${unit.lesson_id}/`);
    }
    const delivered = await page
      .locator("[data-unit-lesson]")
      .evaluateAll((anchors) =>
        anchors.map((anchor) => anchor.getAttribute("href")!),
      );
    for (const href of new Set(delivered)) {
      expect((await request.get(href)).ok(), href).toBe(true);
    }
    await core
      .locator(`a[href="${prefix}/learn/${modellingLine[0]}/"]`)
      .first()
      .click();
    await expect(page).toHaveURL(`${prefix}/learn/${modellingLine[0]}/`);
  });

  test(`readers can open every new worked exercise in ${prefix || "English"}`, async ({
    page,
  }) => {
    for (const id of [...modellingLine, ...mechanismLessons]) {
      expect((await page.goto(`${prefix}/learn/${id}/`))?.status()).toBe(200);
      const answer = page.locator("details[data-worked-answer]").first();
      await expect(answer).not.toHaveAttribute("open", "");
      await answer.locator("summary").focus();
      await page.keyboard.press("Enter");
      await expect(answer).toHaveAttribute("open", "");
      await expect(answer.locator("p").first()).toBeVisible();
    }
  });

  test(`unit prerequisites reveal their collapsed track in ${prefix || "English"}`, async ({
    page,
  }) => {
    await page.goto(`${prefix}${map}`);
    const targetId = await page.evaluate(() => {
      const tracks = [
        ...document.querySelectorAll<HTMLDetailsElement>(
          "details.curriculum-blueprint__track",
        ),
      ];
      for (const source of tracks) {
        for (const link of source.querySelectorAll<HTMLAnchorElement>(
          'a[href^="#unit-"]',
        )) {
          const target = document.getElementById(link.hash.slice(1));
          const targetTrack = target?.closest("details");
          if (targetTrack && targetTrack !== source) {
            tracks.forEach((track) => {
              track.open = track === source;
            });
            link.setAttribute("data-cross-track-test", "");
            return target!.id;
          }
        }
      }
      throw new Error("Expected a cross-track unit prerequisite");
    });
    await page.locator("[data-cross-track-test]").click();
    const target = page.locator(`#${targetId}`);
    await expect(target).toBeVisible();
    await expect(target).toBeInViewport();
    await page.reload();
    await expect(target).toBeVisible();
    await expect(target).toBeInViewport();
  });

  test(`the map, training and biological evidence lessons remain readable at 320px in ${prefix || "English"}`, async ({
    page,
  }) => {
    await page.setViewportSize({ width: 320, height: 850 });
    for (const route of [
      map,
      `/learn/${modellingLine[3]}/`,
      "/learn/drug-discovery-foundations/assay-controls-dose-response/",
      "/learn/mechanism-targets/genetics-to-target-evidence/",
      "/learn/admet-pk/exposure-clearance-pkpd/",
      "/learn/evaluation-and-reproducibility/assay-shift-diagnosis/",
      "/learn/candidate-nomination/evidence-to-validation/",
    ]) {
      await page.goto(`${prefix}${route}`);
      // Reveal content that could hide a long, overflowing prerequisite or formula.
      await page
        .locator("main details")
        .evaluateAll((details) =>
          details.forEach((detail) => detail.setAttribute("open", "")),
        );
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
    }
  });

  test(`the home and Labs entries reach the curriculum and independent sandbox in ${prefix || "English"}`, async ({
    page,
  }) => {
    await page.goto(prefix ? `${prefix}/` : "/");
    const mapLink = page.locator(`main a[href^="${prefix}${map}"]`).first();
    await expect(mapLink).toBeVisible();
    await mapLink.click();
    await expect(page.locator('[data-learning-path="core"]')).toBeVisible();
    await page.goto(`${prefix}/labs/`);
    await page
      .locator(`main a[href="${prefix}/learn/${modellingLine[3]}/"]`)
      .click();
    await expect(page.locator("lesson-progress")).toHaveAttribute(
      "data-lesson-id",
      modellingLine[3],
    );
  });
}

test("new student lesson completion keeps the existing cross-language storage contract", async ({
  page,
}) => {
  const id = modellingLine[3];
  await page.goto(`/zh-cn/learn/${id}/`);
  await page.getByRole("button", { name: "标记本课完成" }).click();
  await page.locator(`main a[href="/learn/${id}/"]`).click();
  await expect(
    page.getByRole("button", { name: "Mark lesson complete" }),
  ).toHaveAttribute("aria-pressed", "true");
  await page.reload();
  await expect(page.locator("[data-progress-status]")).toHaveText("Completed");
  expect(
    await page.evaluate(() =>
      JSON.parse(localStorage.getItem("aidd-commons:v1:progress")!),
    ),
  ).toEqual({ completed: [id] });
});
