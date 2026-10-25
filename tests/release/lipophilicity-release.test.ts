import { copyFile, mkdir, mkdtemp, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { expect, it } from "vitest";
import { buildPublicRelease } from "../../scripts/release/build.js";

it("ships the data inspector and bilingual guide without raw data or local output", async () => {
  const root = await mkdtemp(join(tmpdir(), "aidd-lipo-release-"));
  const source = join(root, "source");
  const lab = join(source, "labs", "lipophilicity");
  await mkdir(lab, { recursive: true });
  const names = [
    "inspect_data.py",
    "README.md",
    "README.zh-CN.md",
    "tutorial.py",
    "build_notebooks.py",
    "lipophilicity_tutorial.ipynb",
    "lipophilicity_tutorial.zh-CN.ipynb",
  ];
  for (const name of names) {
    await copyFile(`labs/lipophilicity/${name}`, join(lab, name));
  }
  await writeFile(join(lab, "Lipophilicity.csv"), "third-party data\n");
  await writeFile(join(lab, "student-output.json"), "{}\n");
  const result = await buildPublicRelease({
    sourceRoot: source,
    destination: join(root, "public-release"),
    inventoryPath: join(root, "inventory.txt"),
  });
  expect(result.files.map((entry) => entry.path).sort()).toEqual(
    names.map((name) => `labs/lipophilicity/${name}`).sort(),
  );
  expect(result.findings).toEqual([]);
});
