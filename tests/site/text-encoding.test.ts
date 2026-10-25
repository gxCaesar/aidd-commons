import { spawnSync } from "node:child_process";
import { mkdir, mkdtemp, readFile, symlink, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { fileURLToPath } from "node:url";

import { describe, expect, it } from "vitest";
import { parse } from "yaml";

import { scanTextEncoding } from "../../scripts/quality/check-text-encoding.js";

const repositoryRoot = fileURLToPath(new URL("../..", import.meta.url));
const fixtures = join(repositoryRoot, "tests/site/fixtures/text-encoding");
const validSource = join(fixtures, "valid");

describe("production text encoding", () => {
  it("accepts valid Chinese and other Unicode without restricting non-ASCII text", async () => {
    await expect(
      scanTextEncoding({ sourceRoot: validSource }),
    ).resolves.toEqual({
      sourceFilesScanned: 1,
      renderedHtmlFilesScanned: 0,
      findings: [],
    });
  });

  it("locates a literal replacement character in production source", async () => {
    const scan = await scanTextEncoding({
      sourceRoot: join(fixtures, "known-bad/literal"),
    });
    expect(scan.sourceFilesScanned).toBe(1);
    expect(scan.findings).toEqual([
      {
        stage: "source",
        path: "site/src/pages/zh-cn/index.astro",
        rule: "replacement-character",
        line: 2,
        column: 6,
      },
    ]);
  });

  it("rejects invalid UTF-8 bytes rather than silently replacing them during decoding", async () => {
    const scan = await scanTextEncoding({
      sourceRoot: join(fixtures, "known-bad/invalid-utf8"),
    });
    expect(scan.findings).toEqual([
      {
        stage: "source",
        path: "site/src/pages/zh-cn/index.astro",
        rule: "invalid-utf8",
      },
    ]);
  });

  it("finds a literal replacement character in rendered text", async () => {
    const scan = await scanTextEncoding({
      sourceRoot: validSource,
      renderedRoot: join(fixtures, "known-bad/rendered-literal"),
    });
    expect(scan.renderedHtmlFilesScanned).toBe(1);
    expect(scan.findings).toEqual([
      {
        stage: "rendered",
        path: "index.html",
        rule: "replacement-character",
        line: 1,
        column: 6,
      },
    ]);
  });

  it("decodes both hexadecimal and decimal replacement-character entities in rendered text", async () => {
    const scan = await scanTextEncoding({
      sourceRoot: validSource,
      renderedRoot: join(fixtures, "known-bad/rendered-entities"),
    });
    expect(scan.findings).toEqual(
      [1, 2].map((line) => ({
        stage: "rendered",
        path: "index.html",
        rule: "replacement-entity",
        line,
        column: 6,
      })),
    );
  });

  it("checks reader text rather than HTML attributes, comments or script/style/template contents", async () => {
    const renderedRoot = await mkdtemp(join(tmpdir(), "aidd-encoding-html-"));
    await writeFile(
      join(renderedRoot, "index.html"),
      '<p title="&#xfffd;">正常中文 &amp;#xfffd;</p><!-- &#xfffd; --><script>const example = "&#xfffd;";</script><style>/* &#xfffd; */</style><template><p>&#xfffd;</p><template>&#xfffd;</template></template><p>仍然正常。</p>',
    );
    const scan = await scanTextEncoding({
      sourceRoot: validSource,
      renderedRoot,
    });
    expect(scan.findings).toEqual([]);
  });

  it("rejects numeric references that HTML maps to the replacement character", async () => {
    const renderedRoot = await mkdtemp(join(tmpdir(), "aidd-encoding-scalar-"));
    await writeFile(
      join(renderedRoot, "index.html"),
      "<p>&#0; &#xD800; &#x110000;</p>",
    );
    const scan = await scanTextEncoding({
      sourceRoot: validSource,
      renderedRoot,
    });
    expect(scan.findings.map((finding) => finding.rule)).toEqual([
      "replacement-entity",
      "replacement-entity",
      "replacement-entity",
    ]);
  });

  it("excludes test fixtures, private/cache trees, binaries and symlinks from production coverage", async () => {
    const sourceRoot = await mkdtemp(join(tmpdir(), "aidd-encoding-scope-"));
    const files = new Map([
      ["site/src/pages/index.astro", "<p>正常中文。</p>"],
      ["tests/site/fixtures/known-bad/example.mdx", "\uFFFD"],
      ["site/src/node_modules/example/index.js", "\uFFFD"],
      ["docs/tmp/internal.md", "\uFFFD"],
      ["docs/claude-codex-workflow-log.md", "\uFFFD"],
      ["site/public/example.png", "\uFFFD"],
    ]);
    for (const [path, text] of files) {
      await mkdir(join(sourceRoot, path, ".."), { recursive: true });
      await writeFile(join(sourceRoot, path), text);
    }
    await symlink(
      join(sourceRoot, "docs/tmp/internal.md"),
      join(sourceRoot, "site/src/pages/private.mdx"),
    );
    const scan = await scanTextEncoding({ sourceRoot });
    expect(scan.sourceFilesScanned).toBe(1);
    expect(scan.findings).toEqual([]);
  });

  it("fails rather than reporting success for an empty source or rendered scan", async () => {
    const empty = await mkdtemp(join(tmpdir(), "aidd-encoding-empty-"));
    await expect(scanTextEncoding({ sourceRoot: empty })).rejects.toThrow(
      "No production text files",
    );
    await expect(
      scanTextEncoding({ sourceRoot: validSource, renderedRoot: empty }),
    ).rejects.toThrow("No rendered HTML files");
  });

  it("returns a failing CLI status with coverage and a precise diagnostic for a known defect", () => {
    const result = spawnSync(
      process.execPath,
      [
        "node_modules/tsx/dist/cli.mjs",
        "scripts/quality/check-text-encoding.ts",
        "--source",
        join(fixtures, "known-bad/literal"),
      ],
      { cwd: repositoryRoot, encoding: "utf8" },
    );
    expect(result.status).toBe(1);
    expect(result.stdout).toContain("1 files scanned");
    expect(result.stderr).toContain(
      "source:site/src/pages/zh-cn/index.astro:2:6: replacement-character",
    );
  });

  it("runs the source/rendered gate after the local and hosted site builds", async () => {
    const manifest = JSON.parse(
      await readFile(join(repositoryRoot, "package.json"), "utf8"),
    );
    expect(manifest.scripts["text:check"]).toBe(
      "tsx scripts/quality/check-text-encoding.ts",
    );
    expect(
      manifest.scripts.check.indexOf("pnpm text:check --rendered site/dist"),
    ).toBeGreaterThan(manifest.scripts.check.indexOf("pnpm --dir site build"));
    const workflow = parse(
      await readFile(join(repositoryRoot, ".github/workflows/ci.yml"), "utf8"),
    ) as {
      jobs: Record<string, { steps: { run?: string }[] }>;
    };
    const commands = workflow.jobs["links-and-citations"].steps.map(
      (step) => step.run,
    );
    expect(
      commands.indexOf("pnpm text:check --rendered site/dist"),
    ).toBeGreaterThan(commands.indexOf("pnpm --dir site build"));
  });
});
