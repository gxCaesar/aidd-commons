import { mkdir, mkdtemp, readFile, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import { dirname, join } from "node:path";
import { expect, it } from "vitest";
import { buildPublicRelease } from "../../scripts/release/build.js";

it("ships both editable foundation notebook pairs without student execution output", async () => {
  const root = await mkdtemp(join(tmpdir(), "aidd-foundation-notebooks-"));
  const sourceRoot = join(root, "source");
  const expected = [
    "labs/student_modelling/build_notebooks.py",
    "labs/student_modelling/student_modelling_tutorial.ipynb",
    "labs/student_modelling/student_modelling_tutorial.zh-CN.ipynb",
    "labs/molecule_representations/build_notebooks.py",
    "labs/molecule_representations/representation_inspector.ipynb",
    "labs/molecule_representations/representation_inspector.zh-CN.ipynb",
  ];
  for (const path of [
    ...expected,
    "labs/student_modelling/executed.ipynb",
    "labs/molecule_representations/student-report.json",
  ]) {
    await mkdir(dirname(join(sourceRoot, path)), { recursive: true });
    await writeFile(
      join(sourceRoot, path),
      path.endsWith(".ipynb")
        ? '{"cells": [], "nbformat": 4}'
        : "Teaching fixture\n",
    );
  }
  const destination = join(root, "public-release");
  const result = await buildPublicRelease({
    sourceRoot,
    destination,
    inventoryPath: join(root, "inventory.txt"),
  });
  expect(result.files.map((entry) => entry.path).sort()).toEqual(
    [...expected].sort(),
  );
  expect(result.findings).toEqual([]);
  for (const path of expected) {
    expect(await readFile(join(destination, path), "utf8")).toBe(
      await readFile(join(sourceRoot, path), "utf8"),
    );
  }
});
