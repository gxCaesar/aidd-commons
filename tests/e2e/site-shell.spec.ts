import { readFile } from "node:fs/promises";
import { AxeBuilder } from "@axe-core/playwright";
import { expect, test, type Page } from "@playwright/test";
import type { Resource } from "../../site/src/data/resource.js";

const resources = JSON.parse(
  await readFile("site/public/data/resources.v1.json", "utf8"),
) as Resource[];

type Rgb = [number, number, number];

function relativeLuminance([red, green, blue]: Rgb) {
  const channels = [red, green, blue].map((channel) => {
    const normalized = channel / 255;
    return normalized <= 0.04045
      ? normalized / 12.92
      : ((normalized + 0.055) / 1.055) ** 2.4;
  });

  return 0.2126 * channels[0] + 0.7152 * channels[1] + 0.0722 * channels[2];
}

function contrastRatio(foreground: Rgb, background: Rgb) {
  const [lighter, darker] = [
    relativeLuminance(foreground),
    relativeLuminance(background),
  ].sort((left, right) => right - left);

  return (lighter + 0.05) / (darker + 0.05);
}

async function computedContrast(page: Page, selector: string) {
  const colors = await page.locator(selector).evaluate((element) => {
    const parseRgb = (value: string) =>
      value
        .match(/\d+(?:\.\d+)?/g)
        ?.slice(0, 3)
        .map(Number) ?? [];
    const styles = getComputedStyle(element);

    return {
      background: parseRgb(styles.backgroundColor),
      foreground: parseRgb(styles.color),
    };
  });

  if (colors.background.length !== 3 || colors.foreground.length !== 3) {
    throw new Error(
      `Expected opaque RGB action colors, received ${JSON.stringify(colors)}`,
    );
  }

  return contrastRatio(colors.foreground as Rgb, colors.background as Rgb);
}

test("English home exposes the four artifacts and primary product navigation", async ({
  page,
}, testInfo) => {
  await page.goto("/");

  await expect(
    page.getByText("building the most comprehensive open AIDD learning system"),
  ).toBeVisible();
  await expect(
    page.getByRole("link", { name: "Choose a pathway" }),
  ).toHaveAttribute("href", "/learn/foundations/getting-started/");
  await expect(
    page.getByRole("link", { name: "Explore the atlas" }),
  ).toHaveAttribute("href", "/atlas/");

  if (testInfo.project.name === "mobile-chromium") {
    await page.getByRole("button", { name: "Open navigation" }).click();
  }
  for (const label of [
    "Learn",
    "Atlas",
    "Labs",
    "Audit",
    "Report",
    "Contribute",
  ]) {
    await expect(
      page.getByRole("navigation").getByRole("link", { name: label }),
    ).toBeVisible();
  }
  await expect(page.getByRole("link", { name: "中文" })).toHaveAttribute(
    "href",
    "/zh-cn/",
  );
});

test("dark primary actions retain AA text contrast at rest and on hover", async ({
  page,
}) => {
  await page.emulateMedia({ colorScheme: "dark" });
  await page.goto("/");

  const primaryAction = page.getByRole("link", { name: "Choose a pathway" });
  expect(await computedContrast(page, ".button-link")).toBeGreaterThanOrEqual(
    4.5,
  );

  await primaryAction.hover();
  expect(await computedContrast(page, ".button-link")).toBeGreaterThanOrEqual(
    4.5,
  );
});

test("active lesson navigation retains readable text in both themes", async ({
  page,
}) => {
  await page.setViewportSize({ width: 1280, height: 900 });
  for (const colorScheme of ["light", "dark"] as const) {
    await page.emulateMedia({ colorScheme });
    await page.goto("/learn/foundations/getting-started/");
    const selector = 'nav a[aria-current="page"]';
    await expect(page.locator(selector)).toHaveText("Learn");
    expect(await computedContrast(page, selector)).toBeGreaterThanOrEqual(4.5);
    await page.locator(selector).hover();
    expect(await computedContrast(page, selector)).toBeGreaterThanOrEqual(4.5);
  }
});

test("Linux search shortcuts retain AA text contrast in both themes", async ({
  browser,
  baseURL,
}, testInfo) => {
  test.skip(testInfo.project.name !== "chromium", "desktop keyboard shortcut");
  const context = await browser.newContext({
    baseURL,
    viewport: { width: 1280, height: 900 },
    userAgent: `Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/${browser.version()} Safari/537.36`,
  });
  await context.addInitScript(() => {
    Object.defineProperty(navigator, "platform", { get: () => "Linux x86_64" });
  });
  const page = await context.newPage();
  try {
    for (const colorScheme of ["light", "dark"] as const) {
      await page.emulateMedia({ colorScheme });
      await page.goto("/learn/foundations/getting-started/");
      const selector = "site-search button[data-open-modal] > kbd";
      const shortcut = page.locator(selector);
      await expect(shortcut).toHaveText("CtrlK");
      await expect(shortcut).toBeVisible();
      expect(
        await computedContrast(page, selector),
        colorScheme,
      ).toBeGreaterThanOrEqual(4.5);
      await page.locator("site-search button[data-open-modal]").hover();
      expect(
        await computedContrast(page, selector),
        `${colorScheme} hover`,
      ).toBeGreaterThanOrEqual(4.5);
      const results = await new AxeBuilder({ page }).analyze();
      expect(
        results.violations.filter((violation) =>
          ["serious", "critical"].includes(violation.impact ?? ""),
        ),
      ).toEqual([]);
    }
  } finally {
    await context.close();
  }
});

test("Chinese onboarding provides an entry route and all eighteen pathway summaries", async ({
  page,
}) => {
  await page.goto("/zh-cn/");

  await expect(page.getByRole("heading", { name: "从这里开始" })).toBeVisible();
  await expect(
    page.getByRole("heading", { name: "18 条学习路径" }),
  ).toBeVisible();
  await expect(page.locator("[data-track-summary]")).toHaveCount(18);
});

test("atlas query deep-link renders the matching resource", async ({
  page,
}) => {
  await page.goto("/atlas/?kind=dataset");

  await expect(
    page.getByRole("heading", { name: "Scientific Atlas" }),
  ).toBeVisible();
  const cards = page.locator("[data-atlas-results] .resource-card");
  await expect(cards.first()).toBeVisible();
  expect(await cards.count()).toBeGreaterThanOrEqual(1);
  for (const metadata of await cards.locator(".meta-label").allTextContents()) {
    expect(metadata).toMatch(/^dataset ·/u);
  }
  await expect(
    page.getByRole("link", { name: "FreeSolv v0.52" }),
  ).toHaveAttribute("href", "/atlas/freesolv-v0-52/");
  await expect(page).toHaveURL(/kind=dataset/);
});

test("resource-card title links meet the minimum touch target height", async ({
  page,
}) => {
  await page.goto("/atlas/");

  const boxes = await page.locator(".resource-card h2 a").evaluateAll((links) =>
    links.map((link) => {
      const box = link.getBoundingClientRect();
      return { height: box.height, width: box.width };
    }),
  );
  expect(
    boxes,
    `resource-card title link boxes: ${JSON.stringify(boxes)}`,
  ).not.toEqual([]);
  expect(
    boxes.every((box) => box.height >= 44),
    `resource-card title link boxes: ${JSON.stringify(boxes)}`,
  ).toBe(true);
});

test("track and pipeline action links meet the minimum touch target height", async ({
  page,
}) => {
  await page.goto("/");

  for (const selector of [".track-card a", ".pipeline-stage__links a"]) {
    const boxes = await page.locator(selector).evaluateAll((actions) =>
      actions.map((action) => {
        const box = action.getBoundingClientRect();
        return { height: box.height, width: box.width };
      }),
    );

    expect(
      boxes,
      `${selector} action boxes: ${JSON.stringify(boxes)}`,
    ).not.toEqual([]);
    expect(
      boxes.every((box) => box.height >= 44),
      `${selector} action boxes: ${JSON.stringify(boxes)}`,
    ).toBe(true);
  }
});

test("resource detail keeps claim qualifications adjacent to the resource", async ({
  page,
}) => {
  await page.goto("/atlas/freesolv-v0-52/");

  await expect(
    page.getByRole("heading", { name: "FreeSolv v0.52" }),
  ).toBeVisible();
  await expect(
    page
      .locator('section[aria-labelledby="evidence-title"]')
      .getByRole("link", { name: "FreeSolv repository" }),
  ).toBeVisible();
  await expect(
    page.getByText(
      "The v0.52 release metadata does not declare licence terms; master branch licences are not evidence for this version.",
    ),
  ).toBeVisible();
  const caveatSection = page
    .locator("section")
    .filter({ has: page.getByRole("heading", { name: "Caveats" }) });
  await expect(
    caveatSection.getByRole("link", { name: "FreeSolv release DOI" }).first(),
  ).toBeVisible();
  await expect(
    page.getByText("No licence claim is currently verified."),
  ).toBeVisible();
  await expect(page.getByText("No acknowledgements recorded.")).toBeVisible();
  const resource = resources.find((record) => record.id === "freesolv-v0-52")!;
  await expect(
    page.getByText(`Last verified: ${resource.last_verified}`),
  ).toBeVisible();
});

test("Starlight pages retain links to every product area", async ({
  page,
}, testInfo) => {
  test.skip(testInfo.project.name !== "chromium", "desktop-only assertion");

  const productAreas = [
    ["Learn", "/learn/foundations/getting-started/"],
    ["Atlas", "/atlas/"],
    ["Labs", "/labs/"],
    ["Audit", "/audit/"],
    ["Report", "/report/"],
    ["Contribute", "/contribute/"],
  ] as const;

  for (const route of [
    "/learn/foundations/getting-started/",
    "/atlas/freesolv-v0-52/",
  ]) {
    await page.goto(route);
    const sidebar = page.locator('nav[aria-label="Main"]');

    for (const [label, href] of productAreas) {
      await expect(sidebar.getByRole("link", { name: label })).toHaveAttribute(
        "href",
        href,
      );
    }
  }
});

test("lesson completion persists in the browser", async ({ page }) => {
  await page.goto("/learn/foundations/getting-started/");

  const completionButton = page.getByRole("button", {
    name: "Mark lesson complete",
  });
  await completionButton.click();
  await expect(completionButton).toHaveAttribute("aria-pressed", "true");
  await page.reload();
  await expect(
    page.getByRole("button", { name: "Mark lesson complete" }),
  ).toHaveAttribute("aria-pressed", "true");
  await expect
    .poll(() =>
      page.evaluate(() => localStorage.getItem("aidd-commons:v1:progress")),
    )
    .toContain("foundations/getting-started");
});

test("coverage audit filters a track and opens adjacent evidence by keyboard", async ({
  page,
}) => {
  await page.goto("/audit/");

  await expect(
    page.getByRole("heading", { name: "AIDD coverage audit" }),
  ).toBeVisible();
  await expect(page.getByText("Claim status: not established")).toBeVisible();

  await page
    .getByLabel("Track", { exact: true })
    .selectOption("representations");
  await page
    .getByLabel("Topic", { exact: true })
    .selectOption("t05-small-molecule-representation");
  await page.getByLabel("Direct observations only").check();
  await expect(page).toHaveURL(
    /track=representations.*topic=t05-small-molecule-representation/,
  );

  const cell = page.locator(
    '[data-provider-id="teachopencadd"][data-topic-id="t05-small-molecule-representation"]',
  );
  await expect(cell).toBeVisible();
  // The count follows the provider record, which grew from one talktorial to
  // seven as the survey read further. The keyboard behaviour is what is tested.
  const evidenceSummary = cell.getByText(/^Evidence \(\d+\)$/);
  await evidenceSummary.focus();
  await page.keyboard.press("Enter");
  await expect(cell.locator("details")).toHaveAttribute("open", "");
  await expect(
    cell.getByRole("link", {
      name: "T007 Ligand-based screening — machine learning",
    }),
  ).toHaveAttribute(
    "href",
    "https://projects.volkamerlab.org/teachopencadd/talktorials/T007_compound_activity_machine_learning.html",
  );
});

test("mobile coverage bounds remain readable inside a local scroll region", async ({
  page,
}, testInfo) => {
  test.skip(
    testInfo.project.name !== "mobile-chromium",
    "mobile-only assertion",
  );
  await page.setViewportSize({ width: 320, height: 720 });
  await page.goto("/audit/");
  // Wider fallback glyphs expose the same header min-content pressure as Linux.
  await page.evaluate(() => {
    document.documentElement.style.fontFamily = "Verdana, sans-serif";
  });
  for (const selector of [".nav-toggle", ".theme-toggle"]) {
    const control = page.locator(selector);
    await expect(control).toBeVisible();
    const size = await control.evaluate((element) => {
      const box = element.getBoundingClientRect();
      return {
        width: box.width,
        height: box.height,
        clientWidth: element.clientWidth,
        scrollWidth: element.scrollWidth,
        clientHeight: element.clientHeight,
        scrollHeight: element.scrollHeight,
      };
    });
    expect(size.width, selector).toBeGreaterThanOrEqual(44);
    expect(size.height, selector).toBeGreaterThanOrEqual(44);
    expect(size.scrollWidth, selector).toBeLessThanOrEqual(size.clientWidth);
    expect(size.scrollHeight, selector).toBeLessThanOrEqual(size.clientHeight);
  }

  const publication = page.locator("[data-correction-window]");
  await expect(publication.locator("time")).toBeVisible();
  const publicationDimensions = await publication.evaluate((element) => ({
    clientWidth: element.clientWidth,
    scrollWidth: element.scrollWidth,
  }));
  expect(
    publicationDimensions.scrollWidth,
    "published correction-window metadata",
  ).toBeLessThanOrEqual(publicationDimensions.clientWidth);

  const boundsRegion = page.getByRole("region", {
    name: "Coverage bounds by depth threshold",
  });
  await expect(boundsRegion).toHaveAttribute("tabindex", "0");

  const dimensions = await boundsRegion.evaluate((element) => ({
    clientWidth: element.clientWidth,
    scrollWidth: element.scrollWidth,
    pageClientWidth: document.documentElement.clientWidth,
    pageScrollWidth: document.documentElement.scrollWidth,
  }));

  expect(dimensions.scrollWidth).toBeGreaterThan(dimensions.clientWidth);
  expect(dimensions.pageScrollWidth).toBeLessThanOrEqual(
    dimensions.pageClientWidth,
  );
});

test("desktop navigation keeps a visible keyboard focus indicator", async ({
  page,
}, testInfo) => {
  test.skip(testInfo.project.name !== "chromium", "desktop-only assertion");
  await page.goto("/");
  await page.keyboard.press("Tab");

  const outlineStyle = await page.evaluate(
    () => getComputedStyle(document.activeElement as Element).outlineStyle,
  );
  expect(outlineStyle).toBe("solid");
});

test("desktop resource detail panels stay inside the article width", async ({
  page,
}, testInfo) => {
  test.skip(testInfo.project.name !== "chromium", "desktop-only assertion");
  await page.setViewportSize({ width: 1365, height: 900 });
  await page.goto("/atlas/freesolv-v0-52/");

  const detail = page.locator(".resource-detail");
  const detailBox = await detail.boundingBox();
  const detailRight = (detailBox?.x ?? 0) + (detailBox?.width ?? 0);
  const overflow = await detail.locator(":scope > section").evaluateAll(
    (sections, allowedRight) =>
      sections
        .map((section, index) => ({
          index,
          right: section.getBoundingClientRect().right,
        }))
        .filter((section) => section.right > allowedRight + 1),
    detailRight,
  );

  expect(
    overflow,
    `detail right edge: ${detailRight}; overflowing sections: ${JSON.stringify(overflow)}`,
  ).toEqual([]);
});

test("mobile navigation remains operable", async ({ page }, testInfo) => {
  test.skip(
    testInfo.project.name !== "mobile-chromium",
    "mobile-only assertion",
  );
  await page.setViewportSize({ width: 320, height: 720 });
  await page.goto("/");

  await page.getByRole("button", { name: "Open navigation" }).click();
  await expect(
    page.getByRole("navigation").getByRole("link", { name: "Atlas" }),
  ).toBeVisible();
});

test("mobile dropdown does not shrink the brand at 320 CSS pixels", async ({
  page,
}, testInfo) => {
  test.skip(
    testInfo.project.name !== "mobile-chromium",
    "mobile-only assertion",
  );
  await page.setViewportSize({ width: 320, height: 720 });
  await page.goto("/");

  const brand = page.getByRole("link", { name: "AIDD Commons" });
  const closedBox = await brand.boundingBox();
  await page.getByRole("button", { name: "Open navigation" }).click();
  const openBox = await brand.boundingBox();

  const boxMessage = `brand boxes: ${JSON.stringify({ closedBox, openBox })}`;
  expect(closedBox?.height, boxMessage).toBeGreaterThanOrEqual(44);
  expect(openBox?.height, boxMessage).toBeGreaterThanOrEqual(44);
  expect(openBox?.width, boxMessage).toBeGreaterThanOrEqual(
    (closedBox?.width ?? 0) - 1,
  );
});

test("home has no serious or critical accessibility violations", async ({
  page,
}) => {
  await page.goto("/");

  const results = await new AxeBuilder({ page }).analyze();
  const blockingViolations = results.violations.filter((violation) =>
    ["serious", "critical"].includes(violation.impact ?? ""),
  );
  expect(blockingViolations).toEqual([]);
});

test("coverage audit has no serious or critical accessibility violations", async ({
  page,
}) => {
  await page.goto("/audit/");

  const results = await new AxeBuilder({ page }).analyze();
  const blockingViolations = results.violations.filter((violation) =>
    ["serious", "critical"].includes(violation.impact ?? ""),
  );
  expect(blockingViolations).toEqual([]);
});
