import { lstat, readdir, readFile } from "node:fs/promises";
import { basename, extname, join, resolve } from "node:path";

import {
  directoryAllowlist,
  exclusionReason,
  fileAllowlist,
} from "../release/build.js";

const textExtensions = new Set([
  ".astro",
  ".bib",
  ".cff",
  ".cif",
  ".cls",
  ".css",
  ".csv",
  ".html",
  ".ini",
  ".ipynb",
  ".js",
  ".json",
  ".jsonl",
  ".md",
  ".mdx",
  ".mjs",
  ".pdb",
  ".py",
  ".r",
  ".rst",
  ".sh",
  ".sty",
  ".tex",
  ".toml",
  ".ts",
  ".txt",
  ".xml",
  ".yaml",
  ".yml",
]);
const textFileNames = new Set([".gitignore", "LICENSE", "LICENSE-CONTENT"]);
const replacementCharacter = "\uFFFD";

export type EncodingFinding = {
  stage: "source" | "rendered";
  path: string;
  rule: "invalid-utf8" | "replacement-character" | "replacement-entity";
  line?: number;
  column?: number;
};

export type EncodingScan = {
  sourceFilesScanned: number;
  renderedHtmlFilesScanned: number;
  findings: EncodingFinding[];
};

function isTestTree(path: string): boolean {
  return (
    path === "tests" ||
    path.startsWith("tests/") ||
    path === "labs/tests" ||
    path.startsWith("labs/tests/")
  );
}

export async function productionTextFiles(
  sourceRoot: string,
): Promise<string[]> {
  const files = new Set<string>();
  async function visit(path: string): Promise<void> {
    if (isTestTree(path) || exclusionReason(path) !== undefined) return;
    let entry;
    try {
      entry = await lstat(join(sourceRoot, path));
    } catch (error) {
      if ((error as NodeJS.ErrnoException).code === "ENOENT") return;
      throw error;
    }
    // Do not follow links out of the declared production scope.
    if (entry.isDirectory()) {
      for (const name of (await readdir(join(sourceRoot, path))).sort()) {
        await visit(`${path}/${name}`);
      }
    } else if (
      entry.isFile() &&
      (textExtensions.has(extname(path).toLowerCase()) ||
        textFileNames.has(basename(path)))
    ) {
      files.add(path);
    }
  }
  for (const path of [...fileAllowlist, ...directoryAllowlist])
    await visit(path);
  return [...files].sort();
}

function position(
  text: string,
  offset: number,
): { line: number; column: number } {
  const before = text.slice(0, offset);
  const newline = before.lastIndexOf("\n");
  return { line: before.split("\n").length, column: offset - newline };
}

/** HTML text nodes, excluding markup, comments and non-reader script/style/template text. */
function* htmlTextRanges(
  html: string,
): Generator<{ text: string; offset: number }> {
  const tokens =
    /<!--[\s\S]*?(?:-->|$)|<![^>]*>|<\/?([a-z][\w:-]*)\b(?:[^>"']|"[^"]*"|'[^']*')*>|[^<]+|</giu;
  let ignoredTag: string | undefined;
  let templateDepth = 0;
  for (const match of html.matchAll(tokens)) {
    const token = match[0];
    const tag = match[1]?.toLowerCase();
    if (tag !== undefined) {
      const closing = token.startsWith("</");
      if (ignoredTag !== undefined) {
        if (tag === ignoredTag && closing) {
          if (ignoredTag !== "template" || --templateDepth === 0)
            ignoredTag = undefined;
        } else if (
          ignoredTag === "template" &&
          tag === "template" &&
          !closing
        ) {
          templateDepth += 1;
        }
      } else if (!closing && ["script", "style", "template"].includes(tag)) {
        ignoredTag = tag;
        templateDepth = 1;
      }
    } else if (ignoredTag === undefined && !token.startsWith("<!")) {
      yield { text: token, offset: match.index };
    }
  }
}

function textFindings(
  text: string,
  stage: EncodingFinding["stage"],
  path: string,
): EncodingFinding[] {
  const findings: EncodingFinding[] = [];
  const ranges =
    stage === "rendered" ? htmlTextRanges(text) : [{ text, offset: 0 }];
  for (const range of ranges) {
    for (const match of range.text.matchAll(
      new RegExp(replacementCharacter, "gu"),
    )) {
      findings.push({
        stage,
        path,
        rule: "replacement-character",
        ...position(text, range.offset + match.index),
      });
    }
    if (stage !== "rendered") continue;
    for (const entity of range.text.matchAll(
      /&#(?:x([0-9a-f]+)|([0-9]+));?/giu,
    )) {
      const value = Number.parseInt(
        entity[1] ?? entity[2],
        entity[1] === undefined ? 10 : 16,
      );
      // HTML maps invalid scalar references to the replacement character too.
      if (
        value === 0xfffd ||
        value === 0 ||
        value > 0x10ffff ||
        (value >= 0xd800 && value <= 0xdfff)
      ) {
        findings.push({
          stage,
          path,
          rule: "replacement-entity",
          ...position(text, range.offset + entity.index),
        });
      }
    }
  }
  return findings;
}

async function renderedHtmlFiles(root: string, prefix = ""): Promise<string[]> {
  const files: string[] = [];
  for (const entry of await readdir(join(root, prefix), {
    withFileTypes: true,
  })) {
    const path = prefix === "" ? entry.name : `${prefix}/${entry.name}`;
    if (
      entry.name.startsWith(".") ||
      entry.name === "node_modules" ||
      entry.name === "tmp"
    )
      continue;
    if (entry.isDirectory())
      files.push(...(await renderedHtmlFiles(root, path)));
    else if (entry.isFile() && extname(path).toLowerCase() === ".html")
      files.push(path);
  }
  return files.sort();
}

export async function scanTextEncoding(options: {
  sourceRoot: string;
  renderedRoot?: string;
}): Promise<EncodingScan> {
  const source = await productionTextFiles(options.sourceRoot);
  if (source.length === 0)
    throw new Error(
      `No production text files found under ${options.sourceRoot}`,
    );
  const rendered =
    options.renderedRoot === undefined
      ? []
      : await renderedHtmlFiles(options.renderedRoot);
  if (options.renderedRoot !== undefined && rendered.length === 0) {
    throw new Error(
      `No rendered HTML files found under ${options.renderedRoot}`,
    );
  }
  const findings: EncodingFinding[] = [];
  for (const [stage, root, files] of [
    ["source", options.sourceRoot, source],
    ["rendered", options.renderedRoot, rendered],
  ] as const) {
    if (root === undefined) continue;
    for (const path of files) {
      const bytes = await readFile(join(root, path));
      let text: string;
      try {
        text = new TextDecoder("utf-8", { fatal: true }).decode(bytes);
      } catch {
        findings.push({ stage, path, rule: "invalid-utf8" });
        continue;
      }
      findings.push(...textFindings(text, stage, path));
    }
  }
  return {
    sourceFilesScanned: source.length,
    renderedHtmlFilesScanned: rendered.length,
    findings,
  };
}

async function main(): Promise<void> {
  let sourceRoot = ".";
  let renderedRoot: string | undefined;
  const args = process.argv.slice(2);
  for (let index = 0; index < args.length; index += 1) {
    const option = args[index];
    const value = args[++index];
    if (!["--source", "--rendered"].includes(option) || value === undefined) {
      throw new Error(
        "Usage: check-text-encoding.ts [--source <tree>] [--rendered <build>]",
      );
    }
    if (option === "--source") sourceRoot = resolve(value);
    else renderedRoot = resolve(value);
  }
  const scan = await scanTextEncoding({ sourceRoot, renderedRoot });
  console.log(
    `Production text encoding: ${scan.sourceFilesScanned} files scanned.`,
  );
  if (renderedRoot !== undefined)
    console.log(
      `Rendered text encoding: ${scan.renderedHtmlFilesScanned} HTML files scanned.`,
    );
  for (const finding of scan.findings) {
    const location =
      finding.line === undefined ? "" : `:${finding.line}:${finding.column}`;
    console.error(
      `${finding.stage}:${finding.path}${location}: ${finding.rule}`,
    );
  }
  if (scan.findings.length > 0) process.exitCode = 1;
  else console.log("Text encoding checks passed.");
}

if (
  process.argv[1] !== undefined &&
  basename(process.argv[1]) === "check-text-encoding.ts"
) {
  main().catch((error: unknown) => {
    console.error(error instanceof Error ? error.message : String(error));
    process.exitCode = 1;
  });
}
