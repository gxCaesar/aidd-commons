import { copyFile, mkdir, mkdtemp, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import { dirname, join } from "node:path";
import { expect, it } from "vitest";
import { buildPublicRelease } from "../../scripts/release/build.js";

it("curates local configuration helpers without private documents or overrides", async () => {
  const root = await mkdtemp(join(tmpdir(), "aidd-local-config-"));
  const source = join(root, "source");
  const included = [
    "configs/scientific-agents/paperqa-local.json",
    "scripts/agents/check_local_profile.py",
    "labs/paperqa_local/README.md",
    "labs/paperqa_local/corpus.json",
    "labs/paperqa_local/run_smoke.py",
    "labs/paperqa_local/build_notebooks.py",
    "labs/paperqa_local/reviewed-example.json",
    "labs/paperqa_local/paperqa_local_tutorial.ipynb",
    "labs/paperqa_local/paperqa_local_tutorial.zh-CN.ipynb",
  ];
  for (const path of included) {
    await mkdir(dirname(join(source, path)), { recursive: true });
    await copyFile(path, join(source, path));
  }
  await writeFile(
    join(source, "configs/scientific-agents/private-notes.txt"),
    "private",
  );
  await writeFile(join(source, "scripts/agents/private-settings.json"), "{}");
  await writeFile(
    join(source, "labs/paperqa_local/private-run-state.json"),
    "{}",
  );
  const result = await buildPublicRelease({
    sourceRoot: source,
    destination: join(root, "public-release"),
    inventoryPath: join(root, "inventory.txt"),
  });
  expect(result.files.map(({ path }) => path).sort()).toEqual(included.sort());
  expect(result.findings).toEqual([]);
});
