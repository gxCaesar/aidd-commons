import { readdir, readFile } from "node:fs/promises";
import { expect, test } from "@playwright/test";
import { AxeBuilder } from "@axe-core/playwright";

const contentRoot = "site/src/content/docs";
const routes = (
  await Promise.all(
    ["learn", "labs"].map(async (section) =>
      (await readdir(`${contentRoot}/${section}`, { recursive: true }))
        .filter((path) => path.endsWith(".mdx"))
        .map((path) => `/${section}/${path.replace(/\.mdx$/, "")}/`),
    ),
  )
).flat();

test("every canonical lesson and lab has a Chinese page with source links", async ({
  page,
}) => {
  test.setTimeout(120_000);
  for (const route of routes) {
    const response = await page.goto(`/zh-cn${route}`);
    expect(response?.status(), route).toBe(200);
    await expect(page.locator("html")).toHaveAttribute("lang", "zh-CN");
    await expect(page.locator("h1")).toContainText(/[\u3400-\u9fff]/);
    await expect(page.locator(`main a[href="${route}"]`).first()).toBeVisible();
    const english = await readFile(
      `${contentRoot}${route.slice(0, -1)}.mdx`,
      "utf8",
    );
    const sourceUrls = [...english.matchAll(/\]\((https?:\/\/[^\s)]+)\)/g)].map(
      (match) => match[1],
    );
    const links = await page
      .locator("main a")
      .evaluateAll((nodes) => nodes.map((node) => node.getAttribute("href")));
    for (const url of sourceUrls)
      expect(
        links.map((href) => (href === null ? null : decodeURI(href))),
        `${route}: ${url}`,
      ).toContain(decodeURI(url));
  }
});

test("Chinese progress persists into English and keeps localized labels after reload", async ({
  page,
}) => {
  const path = "/learn/representations/biological-representations/";
  await page.goto(`/zh-cn${path}`);
  const button = page.getByRole("button", { name: "标记本课完成" });
  await expect(button).toHaveAttribute("aria-pressed", "false");
  await button.click();
  await expect(page.locator("[data-progress-status]")).toHaveText("已完成");
  await page.reload();
  await expect(button).toHaveAttribute("aria-pressed", "true");
  await expect(page.locator("[data-progress-status]")).toHaveText("已完成");
  await page.goto(path);
  await expect(
    page.getByRole("button", { name: "Mark lesson complete" }),
  ).toHaveAttribute("aria-pressed", "true");
  await expect(page.locator("[data-progress-status]")).toHaveText("Completed");
});

test("Chinese entry routes retain Chinese lessons, resources and lab downloads", async ({
  page,
}) => {
  await page.goto("/zh-cn/pathways/representations/");
  await page
    .locator(
      'main a[href="/zh-cn/learn/representations/small-molecule-representations/"]',
    )
    .click();
  await page.locator("[data-lesson-resources] summary").click();
  await expect(page.locator("[data-lesson-resources]")).toContainText(
    "访问资源",
  );
  await expect(
    page.locator('[data-lesson-resources] a[href="/atlas/tool-rdkit/"]'),
  ).toBeVisible();
  await page.goto("/zh-cn/labs/");
  await page
    .locator('main a[href="/zh-cn/labs/molecule-representation-inspector/"]')
    .click();
  await expect(
    page.getByRole("heading", { name: "下载教学材料" }),
  ).toBeVisible();
  await expect(
    page.locator(
      '[data-lab-downloads] a[href="/downloads/labs/molecule_representations/examples.csv"]',
    ),
  ).toBeVisible();
});

test("language navigation preserves the lesson and untranslated section targets", async ({
  page,
  isMobile,
}) => {
  await page.goto("/learn/representations/biological-representations/");
  // Both sidebar and language selection must work without scripting our links.
  if (isMobile)
    await page.getByRole("button", { name: "Menu", exact: true }).click();
  await page
    .locator("starlight-lang-select select:visible")
    .selectOption({ label: "简体中文" });
  await expect(page).toHaveURL(
    /\/zh-cn\/learn\/representations\/biological-representations\/$/,
  );
  const sidebar = page.locator("#starlight__sidebar");
  await expect(
    sidebar.locator('a[href="/zh-cn/learn/foundations/getting-started/"]'),
  ).toHaveCount(1);
  await expect(sidebar.locator('a[href="/zh-cn/labs/"]')).toHaveCount(1);
  for (const section of ["atlas", "audit", "report", "contribute"]) {
    await expect(sidebar.locator(`a[href="/${section}/"]`)).toHaveCount(1);
    await expect(sidebar.locator(`a[href="/zh-cn/${section}/"]`)).toHaveCount(
      0,
    );
  }
  if (isMobile)
    await page.getByRole("button", { name: "菜单", exact: true }).click();
  await page
    .locator("starlight-lang-select select:visible")
    .selectOption({ label: "English" });
  await expect(page).toHaveURL(
    /(?<!zh-cn)\/learn\/representations\/biological-representations\/$/,
  );
  await expect(page.locator("html")).toHaveAttribute("lang", "en");
  await expect(
    sidebar.locator('a[href="/learn/foundations/getting-started/"]'),
  ).toHaveCount(1);
  await expect(
    sidebar.locator('a[href="/zh-cn/learn/foundations/getting-started/"]'),
  ).toHaveCount(0);
  await page.goto("/zh-cn/learn/foundations/getting-started/");
  await expect(
    page.locator('[data-lesson-route="core"] [data-next-lesson]'),
  ).toHaveAttribute("href", "/zh-cn/learn/foundations/first-session/");
});

test("Chinese lessons are accessible at narrow widths", async ({ page }) => {
  await page.setViewportSize({ width: 320, height: 850 });
  await page.goto("/zh-cn/learn/representations/biological-representations/");
  await page.locator("[data-lesson-resources] summary").click();
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= window.innerWidth,
    ),
  ).toBe(true);
  const audit = await new AxeBuilder({ page }).analyze();
  expect(
    audit.violations.filter(
      ({ impact }) => impact === "critical" || impact === "serious",
    ),
  ).toEqual([]);
});
