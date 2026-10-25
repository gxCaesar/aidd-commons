import {
  copyFile,
  mkdir,
  mkdtemp,
  readFile,
  writeFile,
} from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { fileURLToPath } from "node:url";

import { describe, expect, it } from "vitest";

import { buildPublicRelease } from "../../scripts/release/build.js";
import { scanPublicTree } from "../../scripts/release/hygiene.js";

const fixtures = fileURLToPath(new URL("./fixtures/", import.meta.url));
const valid = join(fixtures, "valid-public-roadmap");
const bad = join(fixtures, "known-bad/internal-checkpoint");
const roadmap = "docs/ROADMAP_V0.2.md";
const publicRoadmap = "docs/PUBLIC_ROADMAP.md";
const pointer = await readFile(join(valid, roadmap), "utf8");
const checkpoint = await readFile(join(bad, "notes.md"), "utf8");

async function sourceWithCheckpoint(withPublic = true) {
  const source = await mkdtemp(join(tmpdir(), "aidd-roadmap-source-"));
  await mkdir(join(source, "docs"));
  await writeFile(join(source, roadmap), checkpoint);
  if (withPublic) {
    await copyFile(join(valid, publicRoadmap), join(source, publicRoadmap));
  }
  return source;
}

async function build(sourceRoot: string) {
  const workspace = await mkdtemp(join(tmpdir(), "aidd-roadmap-export-"));
  const destination = join(workspace, "public-release");
  const result = await buildPublicRelease({
    sourceRoot,
    destination,
    inventoryPath: join(workspace, "inventory.txt"),
  });
  return { destination, result };
}

describe("public roadmap and private checkpoint separation", () => {
  it("rejects an explicitly internal Markdown checkpoint at any filename", async () => {
    expect(await scanPublicTree(bad)).toEqual([
      expect.objectContaining({
        path: "notes.md",
        rule: "internal-checkpoint-content",
      }),
    ]);
  });

  it("accepts a nonempty public roadmap and the deterministic compatibility pointer", async () => {
    expect(pointer).toContain("PUBLIC_ROADMAP.md#rmd17-system-state");
    expect(pointer).toContain(
      "PUBLIC_ROADMAP.md#pk-source-screening-2026-09-12",
    );
    expect(
      (await readFile(join(valid, publicRoadmap), "utf8")).length,
    ).toBeGreaterThan(100);
    expect(await scanPublicTree(valid)).toEqual([]);
  });

  it("rejects the old reserved path even if its private checkpoint lacks a visibility marker", async () => {
    const source = await sourceWithCheckpoint();
    await writeFile(
      join(source, roadmap),
      checkpoint.replace("<!-- visibility: internal -->\n", ""),
    );
    expect(await scanPublicTree(source)).toEqual([
      expect.objectContaining({
        path: roadmap,
        rule: "internal-checkpoint-content",
      }),
    ]);
  });

  it("preserves the source checkpoint and emits one public pointer inventory entry", async () => {
    const source = await sourceWithCheckpoint();
    const { destination, result } = await build(source);
    expect(await readFile(join(source, roadmap), "utf8")).toBe(checkpoint);
    expect(await readFile(join(destination, roadmap), "utf8")).toBe(pointer);
    expect(await readFile(join(destination, publicRoadmap), "utf8")).toBe(
      await readFile(join(valid, publicRoadmap), "utf8"),
    );
    expect(result.files.filter((entry) => entry.path === roadmap)).toHaveLength(
      1,
    );
    expect(
      result.skipped.some((entry) => entry.startsWith(`${roadmap} (`)),
    ).toBe(true);
    expect(result.findings).toEqual([]);
    expect(await scanPublicTree(destination)).toEqual([]);
  });

  it("re-exports the already curated tree without needing the private checkpoint", async () => {
    const first = await build(await sourceWithCheckpoint());
    const second = await build(first.destination);
    expect(await readFile(join(second.destination, roadmap), "utf8")).toBe(
      pointer,
    );
    expect(second.result.files).toEqual(first.result.files);
    expect(second.result.findings).toEqual([]);
    expect(
      second.result.files.filter((entry) => entry.path === roadmap),
    ).toHaveLength(1);
    expect(
      second.result.skipped.some((entry) => entry.startsWith(`${roadmap} (`)),
    ).toBe(true);
  });

  it("refuses to replace a private checkpoint before the public summary exists", async () => {
    const source = await sourceWithCheckpoint(false);
    await expect(build(source)).rejects.toThrow("PUBLIC_ROADMAP.md");
    expect(await readFile(join(source, roadmap), "utf8")).toBe(checkpoint);
  });
});
