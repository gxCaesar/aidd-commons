import { readFile } from "node:fs/promises";
import { expect, test } from "@playwright/test";
import type { Resource } from "../../site/src/data/resource.js";
import { parse } from "yaml";
import type { Curriculum } from "../../scripts/curriculum/curriculum.js";
import {
  filterResources,
  parseAtlasQuery,
} from "../../site/src/lib/atlas-state.js";

const resources = JSON.parse(
  await readFile("site/public/data/resources.v1.json", "utf8"),
) as Resource[];
const curriculum = parse(
  await readFile("catalog/curriculum/tracks.yaml", "utf8"),
) as Curriculum;

test("lab pages expose curated downloadable artifacts with exact content", async ({
  page,
  request,
}) => {
  const cases = [
    [
      "freesolv-honest-baselines",
      "labs/freesolv/freesolv_honest_baselines.ipynb",
    ],
    ["chembl-egfr-representation-baselines", "labs/chembl_egfr/protocol.json"],
    [
      "rmd17-system-state-energy-baselines",
      "labs/rmd17_system_state/locked-summary.json",
    ],
    ["pool-budget-campaign", "labs/pool_budget/real-protocol.json"],
    [
      "molecule-representation-inspector",
      "labs/molecule_representations/examples.csv",
    ],
    // A deposited structure file must arrive byte for byte, or the check that
    // verifies its SHA-256 stops the reader's run.
    ["egfr-structure-evidence", "labs/egfr_structures/structures/1M17.cif"],
    ["egfr-structure-evidence", "labs/egfr_structures/entries.json"],
  ];
  for (const [slug, path] of cases) {
    await page.goto(`/labs/${slug}/`);
    await expect(
      page.locator(`[data-lab-downloads] a[href="/downloads/${path}"]`),
    ).toBeVisible();
    const response = await request.get(`/downloads/${path}`);
    expect(response.status()).toBe(200);
    expect(await response.text()).toBe(await readFile(path, "utf8"));
  }
  expect(
    (
      await request.get("/downloads/labs/chembl_egfr/results/pretest.json")
    ).status(),
  ).toBe(404);
});

test("every lesson exposes its registered sources and pathway core sources", async ({
  page,
}) => {
  test.setTimeout(120_000);
  for (const track of curriculum.tracks) {
    const coreSources = track.lessons
      .filter((lesson) => lesson.type === "core-source-path")
      .flatMap((lesson) => lesson.source_ids);
    for (const lesson of track.lessons.filter(
      (lesson) => lesson.type !== "core-source-path",
    )) {
      await page.goto(`/learn/${track.id}/${lesson.id}/`);
      const section = page.locator("[data-lesson-resources]");
      await expect(section).toBeVisible();
      const hrefs = await section
        .locator("a")
        .evaluateAll((links) => links.map((link) => link.getAttribute("href")));
      for (const id of [...lesson.source_ids, ...coreSources]) {
        expect(hrefs, `${track.id}/${lesson.id}: ${id}`).toContain(
          `/atlas/${id}/`,
        );
      }
    }
  }
});

test("all Atlas cards expose their canonical URL before and after filtering", async ({
  page,
}) => {
  await page.goto("/atlas/");
  for (const resource of resources) {
    const card = page.locator(".resource-card").filter({
      has: page.locator(`h2 a[href="/atlas/${resource.id}/"]`),
    });
    await expect(
      card.getByRole("link", { name: "Visit resource", exact: true }),
    ).toHaveAttribute("href", resource.canonical_url);
  }
  await page
    .getByRole("searchbox", { name: "Search", exact: true })
    .fill("RDKit");
  // The expected count comes from the same filter the page runs, because the
  // Atlas gained an RDKit Cookbook record after this test first counted one card.
  const expected = filterResources(
    resources,
    parseAtlasQuery(new URLSearchParams("q=RDKit")),
  );
  expect(expected.length).toBeGreaterThan(0);
  await expect(page.locator(".resource-card")).toHaveCount(expected.length);
  await expect(
    page
      .locator(".resource-card")
      .filter({ has: page.locator('h2 a[href="/atlas/tool-rdkit/"]') })
      .getByRole("link", { name: "Visit resource", exact: true }),
  ).toHaveAttribute("href", "https://github.com/rdkit/rdkit");
});

test("Atlas card resource links work without JavaScript", async ({
  browser,
}) => {
  const context = await browser.newContext({ javaScriptEnabled: false });
  const page = await context.newPage();
  await page.goto("http://127.0.0.1:4324/atlas/");
  await expect(
    page.getByRole("link", { name: "Visit resource", exact: true }),
  ).toHaveCount(resources.length);
  await context.close();
});

test("detail quick links expose every distinct registered URL without duplication", async ({
  page,
}) => {
  test.setTimeout(120_000);
  for (const resource of resources) {
    await page.goto(`/atlas/${resource.id}/`);
    const section = page.getByRole("region", {
      name: "Resource links",
      exact: true,
    });
    await expect(section).toBeVisible();
    const actual = await section
      .locator("a")
      .evaluateAll((links) => links.map((link) => link.getAttribute("href")));
    const expected = [
      ...new Set([
        resource.canonical_url,
        ...resource.identifiers.flatMap((identifier) =>
          identifier.url ? [identifier.url] : [],
        ),
        ...resource.evidence.map((evidence) => evidence.url),
      ]),
    ];
    expect(actual.sort(), resource.id).toEqual(expected.sort());
  }
});
