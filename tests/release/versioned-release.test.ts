import { mkdtemp, readFile, rm } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { fileURLToPath } from "node:url";

import { parse } from "yaml";
import { afterAll, expect, it } from "vitest";

import { buildPublicRelease } from "../../scripts/release/build.js";

const repositoryRoot = fileURLToPath(new URL("../..", import.meta.url));
let workspace: string | undefined;

afterAll(async () => {
  if (workspace !== undefined) {
    await rm(workspace, { recursive: true, force: true });
  }
});

it("ships consistent release metadata, the report addendum, and the historical citation", async () => {
  workspace = await mkdtemp(join(tmpdir(), "aidd-versioned-release-"));
  const destination = join(workspace, "public-release");
  await buildPublicRelease({
    sourceRoot: repositoryRoot,
    destination,
    inventoryPath: join(workspace, "inventory.txt"),
  });
  const read = (path: string) => readFile(join(destination, path), "utf8");
  const root = JSON.parse(await read("package.json"));
  const site = JSON.parse(await read("site/package.json"));
  const citation = parse(await read("CITATION.cff"));
  expect(root.version).toMatch(/^\d+\.\d+\.\d+(?:-rc\.\d+)?$/u);
  expect(site.version).toBe(root.version);
  expect(citation.version).toBe(root.version);
  expect(citation["preferred-citation"].version).toBe(root.version);
  expect(citation["repository-code"]).toBe(
    "https://github.com/gxCaesar/aidd-commons",
  );
  expect(citation.url).toBe("https://gxcaesar.github.io/aidd-commons/");
  const pythonVersion = (await read("pyproject.toml")).match(
    /^version = "([^"]+)"$/mu,
  )?.[1];
  expect(pythonVersion).toBe(root.version.replace("-rc.", "rc"));
  const archive = parse(await read("report/CITATION-v0.1.cff"));
  expect(archive.version).toBe("0.1.0");
  expect(archive["date-released"]).toBe("2026-09-04");
  await read("report/aidd-commons-v0.2-addendum.md");
  await read("CHANGELOG.md");
}, 30_000);
