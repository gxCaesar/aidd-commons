import { access, mkdir, readFile, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { mkdtemp } from "node:fs/promises";

import { describe, expect, it } from "vitest";

async function loadBuilder() {
  return import("../../scripts/release/build.js");
}

async function fixtureSource(): Promise<string> {
  const root = await mkdtemp(join(tmpdir(), "aidd-release-source-"));
  await Promise.all([
    mkdir(join(root, "catalog", "comparisons", "systems"), {
      recursive: true,
    }),
    mkdir(join(root, "catalog", "schema"), { recursive: true }),
    mkdir(join(root, "scripts", "catalog"), { recursive: true }),
    mkdir(join(root, "scripts", "comparisons"), { recursive: true }),
    mkdir(join(root, "tests", "comparisons"), { recursive: true }),
    mkdir(join(root, "docs"), { recursive: true }),
    mkdir(join(root, ".github", "workflows"), { recursive: true }),
    mkdir(join(root, ".pnpm-store"), { recursive: true }),
    mkdir(join(root, "labs", "freesolv", "results", "splits"), {
      recursive: true,
    }),
    mkdir(join(root, "labs", "molecule_representations"), {
      recursive: true,
    }),
    mkdir(join(root, "labs", "chembl_egfr", "results"), {
      recursive: true,
    }),
    mkdir(join(root, "labs", "rmd17_system_state", "data"), {
      recursive: true,
    }),
    mkdir(join(root, "labs", "rmd17_system_state", "results"), {
      recursive: true,
    }),
    mkdir(join(root, "labs", "src", "aidd_commons", "__pycache__"), {
      recursive: true,
    }),
    mkdir(join(root, ".superpowers"), { recursive: true }),
  ]);
  await Promise.all([
    writeFile(join(root, "README.md"), "# Public release fixture\n"),
    writeFile(join(root, "package.json"), '{"name":"fixture"}\n'),
    writeFile(join(root, "catalog", "schema", "resource.ts"), "export {};\n"),
    writeFile(
      join(root, "catalog", "comparisons", "taxonomy.yaml"),
      "version: comparison.v1\n",
    ),
    writeFile(
      join(root, "catalog", "comparisons", "systems", "aidd-commons.yaml"),
      "id: aidd-commons\n",
    ),
    writeFile(join(root, "scripts", "catalog", "validate.ts"), "export {};\n"),
    writeFile(
      join(root, "scripts", "comparisons", "validate.ts"),
      "export {};\n",
    ),
    writeFile(
      join(root, "tests", "comparisons", "schema.test.ts"),
      "export {};\n",
    ),
    writeFile(join(root, "docs", "task-6-brief.md"), "private task brief\n"),
    writeFile(join(root, "docs", "release-prompt.md"), "private prompt\n"),
    writeFile(
      join(root, ".github", "workflows", "ci.yml"),
      "name: private workflow\n",
    ),
    writeFile(
      join(root, ".github", "PULL_REQUEST_TEMPLATE.md"),
      "# Pull request\n",
    ),
    writeFile(
      join(root, "labs", "src", "aidd_commons", "__pycache__", "module.pyc"),
      "/Users/fixture/private-cache\n",
    ),
    writeFile(
      join(root, ".pnpm-store", "local-package-cache"),
      "local cache\n",
    ),
    writeFile(
      join(root, "labs", "freesolv", "reviewed-results.json"),
      '{"splits":{"scaffold":{"counts":{"train":514}}}}\n',
    ),
    writeFile(
      join(root, "labs", "molecule_representations", "README.md"),
      "# Label-free representation inspector\n",
    ),
    writeFile(
      join(root, "labs", "molecule_representations", "examples.csv"),
      "id,smiles,teaching_point\nethanol,CCO,neutral\n",
    ),
    writeFile(
      join(root, "labs", "molecule_representations", "run_lab.py"),
      'print("representation inspector")\n',
    ),
    writeFile(
      join(root, "labs", "chembl_egfr", "README.md"),
      "# ChEMBL EGFR representation baselines\n",
    ),
    writeFile(
      join(root, "labs", "chembl_egfr", "protocol.json"),
      '{"locked_evaluation":{"state":"not_run"}}\n',
    ),
    writeFile(
      join(root, "labs", "chembl_egfr", "development-summary.json"),
      '{"locked_evaluations":{"primary":"not_run","replication":"not_run"}}\n',
    ),
    writeFile(
      join(root, "labs", "chembl_egfr", "run_lab.py"),
      'print("ChEMBL EGFR lab")\n',
    ),
    writeFile(
      join(root, "labs", "chembl_egfr", "results", "pretest.json"),
      '{"pretest_passed":true}\n',
    ),
    writeFile(
      join(
        root,
        "labs",
        "chembl_egfr",
        "results",
        "locked-evaluation.started.json",
      ),
      '{"status":"started"}\n',
    ),
    writeFile(
      join(root, "labs", "rmd17_system_state", "README.md"),
      "# rMD17 teaching lab\n",
    ),
    writeFile(
      join(root, "labs", "rmd17_system_state", "protocol.json"),
      '{"protocol_id":"rmd17-system-state-v1"}\n',
    ),
    writeFile(
      join(root, "labs", "rmd17_system_state", "development-summary.json"),
      '{"locked_evaluations":{"benzene":"not_run","uracil":"not_run"}}\n',
    ),
    writeFile(
      join(root, "labs", "rmd17_system_state", "run_lab.py"),
      'print("rMD17 lab")\n',
    ),
    writeFile(
      join(root, "labs", "rmd17_system_state", "data", "rmd17_ethanol.npz"),
      "raw coordinates\n",
    ),
    writeFile(
      join(root, "labs", "rmd17_system_state", "results", "pretest.json"),
      '{"pretest_passed":true}\n',
    ),
    writeFile(
      join(
        root,
        "labs",
        "rmd17_system_state",
        "results",
        "locked-evaluation.started.json",
      ),
      '{"status":"started"}\n',
    ),
    writeFile(
      join(
        root,
        "labs",
        "rmd17_system_state",
        "results",
        "locked-metrics.json",
      ),
      '{"results":{"benzene":{}}}\n',
    ),
    writeFile(
      join(root, "labs", "rmd17_system_state", "results", "membership.json"),
      '{"membership":{"train":[1]}}\n',
    ),
    writeFile(
      join(root, "labs", "rmd17_system_state", "results", "predictions.json"),
      '{"predictions":[0.1]}\n',
    ),
    writeFile(
      join(root, "labs", "freesolv", "results", "metrics.json"),
      '{"membership":{"ids":{"test":["mobley_1"]}}}\n',
    ),
    writeFile(
      join(root, "labs", "freesolv", "results", "pretest.json"),
      '{"pretest_passed":true}\n',
    ),
    writeFile(
      join(root, "labs", "freesolv", "results", "splits", "random.csv"),
      "id,smiles,split\nmobley_1,CCO,test\n",
    ),
    writeFile(
      join(root, "labs", "freesolv", "results", "splits", "scaffold.csv"),
      "id,smiles,split\nmobley_1,CCO,test\n",
    ),
    writeFile(join(root, ".superpowers", "private.md"), "private workflow\n"),
  ]);
  return root;
}

describe("curated public release builder", () => {
  it("delivers scientific PDF and PNG without legacy scientific SVG copies", async () => {
    const { buildPublicRelease, exclusionReason } = await loadBuilder();
    const sourceRoot = await fixtureSource();
    const workspace = await mkdtemp(join(tmpdir(), "aidd-figure-output-"));
    const destination = join(workspace, "public-release");
    const delivered = [
      "site/public/figures/current.pdf",
      "site/public/figures/current.png",
      "report/figures/out/current.pdf",
      "site/public/favicon.svg",
    ];
    const legacy = [
      "site/public/figures/legacy.svg",
      "report/figures/out/legacy.svg",
    ];
    for (const path of [...delivered, ...legacy]) {
      await mkdir(join(sourceRoot, path, ".."), { recursive: true });
      await writeFile(join(sourceRoot, path), "Fixture figure asset.\n");
    }
    const result = await buildPublicRelease({
      sourceRoot,
      destination,
      inventoryPath: join(workspace, "inventory.txt"),
    });
    for (const path of delivered) {
      expect(exclusionReason(path)).toBeUndefined();
      await expect(access(join(destination, path))).resolves.toBeUndefined();
    }
    for (const path of legacy) {
      expect(exclusionReason(path)).toMatch(/legacy scientific SVG/);
      await expect(access(join(destination, path))).rejects.toThrow();
      expect(
        result.skipped.some((entry) => entry.startsWith(`${path} (`)),
      ).toBe(true);
      await expect(access(join(sourceRoot, path))).resolves.toBeUndefined();
    }
  });

  it("keeps the project-local collaboration log out of the public copy", async () => {
    const { buildPublicRelease } = await loadBuilder();
    const sourceRoot = await fixtureSource();
    const workspace = await mkdtemp(join(tmpdir(), "aidd-handoff-output-"));
    const destination = join(workspace, "public-release");
    await writeFile(
      join(sourceRoot, "docs", "claude-codex-workflow-log.md"),
      "Local handoff note.\n",
    );
    await buildPublicRelease({
      sourceRoot,
      destination,
      inventoryPath: join(workspace, "inventory.txt"),
    });
    await expect(
      access(join(destination, "docs", "claude-codex-workflow-log.md")),
    ).rejects.toThrow();
  });

  it("copies only allowlisted files and writes MB or GB inventory entries", async () => {
    const { buildPublicRelease } = await loadBuilder();
    const sourceRoot = await fixtureSource();
    const workspace = await mkdtemp(join(tmpdir(), "aidd-release-output-"));
    const destination = join(workspace, "public-release");
    const inventoryPath = join(workspace, "inventory.txt");

    const result = await buildPublicRelease({
      destination,
      inventoryPath,
      sourceRoot,
    });

    await expect(
      access(join(destination, "README.md")),
    ).resolves.toBeUndefined();
    await expect(
      access(join(destination, "catalog", "schema", "resource.ts")),
    ).resolves.toBeUndefined();
    await expect(
      access(join(destination, "catalog", "comparisons", "taxonomy.yaml")),
    ).resolves.toBeUndefined();
    await expect(
      access(
        join(
          destination,
          "catalog",
          "comparisons",
          "systems",
          "aidd-commons.yaml",
        ),
      ),
    ).resolves.toBeUndefined();
    await expect(
      access(join(destination, "scripts", "comparisons", "validate.ts")),
    ).resolves.toBeUndefined();
    await expect(
      access(join(destination, "tests", "comparisons", "schema.test.ts")),
    ).resolves.toBeUndefined();
    await expect(
      access(join(destination, ".superpowers", "private.md")),
    ).rejects.toThrow();
    const inventory = await readFile(inventoryPath, "utf8");
    expect(inventory).toMatch(/\b(?:MB|GB)\b/u);
    expect(inventory).toContain("<0.01 MB");
    expect(inventory).not.toMatch(/\bbytes\b/iu);
    await expect(
      access(join(destination, "docs", "task-6-brief.md")),
    ).rejects.toThrow();
    await expect(
      access(join(destination, "docs", "release-prompt.md")),
    ).rejects.toThrow();
    await expect(
      access(join(destination, ".github", "workflows", "ci.yml")),
    ).resolves.toBeUndefined();
    await expect(
      access(join(destination, ".github", "PULL_REQUEST_TEMPLATE.md")),
    ).resolves.toBeUndefined();
    await expect(
      access(
        join(
          destination,
          "labs",
          "src",
          "aidd_commons",
          "__pycache__",
          "module.pyc",
        ),
      ),
    ).rejects.toThrow();
    await expect(
      access(join(destination, ".pnpm-store", "local-package-cache")),
    ).rejects.toThrow();
    await expect(
      access(join(destination, "labs", "freesolv", "reviewed-results.json")),
    ).resolves.toBeUndefined();
    await expect(
      access(
        join(destination, "labs", "molecule_representations", "README.md"),
      ),
    ).resolves.toBeUndefined();
    await expect(
      access(
        join(destination, "labs", "molecule_representations", "examples.csv"),
      ),
    ).resolves.toBeUndefined();
    await expect(
      access(
        join(destination, "labs", "molecule_representations", "run_lab.py"),
      ),
    ).resolves.toBeUndefined();
    for (const file of [
      "README.md",
      "protocol.json",
      "development-summary.json",
      "run_lab.py",
    ]) {
      await expect(
        access(join(destination, "labs", "chembl_egfr", file)),
      ).resolves.toBeUndefined();
    }
    for (const file of [
      "README.md",
      "protocol.json",
      "development-summary.json",
      "run_lab.py",
    ]) {
      await expect(
        access(join(destination, "labs", "rmd17_system_state", file)),
      ).resolves.toBeUndefined();
    }
    await expect(
      access(
        join(destination, "labs", "chembl_egfr", "results", "pretest.json"),
      ),
    ).rejects.toThrow();
    await expect(
      access(
        join(
          destination,
          "labs",
          "chembl_egfr",
          "results",
          "locked-evaluation.started.json",
        ),
      ),
    ).rejects.toThrow();
    for (const file of [
      join("data", "rmd17_ethanol.npz"),
      join("results", "pretest.json"),
      join("results", "locked-evaluation.started.json"),
      join("results", "locked-metrics.json"),
      join("results", "membership.json"),
      join("results", "predictions.json"),
    ]) {
      await expect(
        access(join(destination, "labs", "rmd17_system_state", file)),
      ).rejects.toThrow();
    }
    await expect(
      access(join(destination, "labs", "freesolv", "results", "metrics.json")),
    ).rejects.toThrow();
    await expect(
      access(join(destination, "labs", "freesolv", "results", "pretest.json")),
    ).rejects.toThrow();
    await expect(
      access(
        join(
          destination,
          "labs",
          "freesolv",
          "results",
          "splits",
          "random.csv",
        ),
      ),
    ).rejects.toThrow();
    await expect(
      access(
        join(
          destination,
          "labs",
          "freesolv",
          "results",
          "splits",
          "scaffold.csv",
        ),
      ),
    ).rejects.toThrow();
    expect(result.findings).toEqual([]);
  });

  it("refuses a non-empty destination without removing its contents", async () => {
    const { buildPublicRelease } = await loadBuilder();
    const sourceRoot = await fixtureSource();
    const workspace = await mkdtemp(join(tmpdir(), "aidd-release-dirty-"));
    const destination = join(workspace, "public-release");
    await mkdir(destination);
    await writeFile(join(destination, "keep.txt"), "preserve this file\n");

    await expect(
      buildPublicRelease({
        destination,
        inventoryPath: join(workspace, "inventory.txt"),
        sourceRoot,
      }),
    ).rejects.toThrow(/not empty/u);
    await expect(readFile(join(destination, "keep.txt"), "utf8")).resolves.toBe(
      "preserve this file\n",
    );
  });
});
