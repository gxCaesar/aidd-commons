import { execFileSync } from "node:child_process";
import { existsSync } from "node:fs";
import {
  access,
  mkdir,
  mkdtemp,
  readdir,
  rm,
  writeFile,
} from "node:fs/promises";
import { tmpdir } from "node:os";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

import { afterAll, beforeAll, describe, expect, it } from "vitest";

import {
  buildPublicRelease,
  directoryAllowlist,
  excludedReleasePaths,
  fileAllowlist,
  intentionalReleaseExclusions,
  isLegacyScientificSvg,
  type ReleaseBuildResult,
} from "../../scripts/release/build.js";

const repositoryRoot = fileURLToPath(new URL("../..", import.meta.url));
// The tracked-file rule is a rule about a repository. A curated export is a
// source tree without its history, so that rule only runs in a checkout.
const isGitCheckout = existsSync(join(repositoryRoot, ".git"));
const livingReportPdf = "aidd-commons-living-report-v0.1.pdf";
const answerSheets = [
  "docs/READER_TRIAL.md",
  "docs/reader-trial/notebook-reader.en.md",
  "docs/reader-trial/notebook-reader.zh-CN.md",
];
const blankObservationForm = "docs/reader-trial/notebook-observation.md";

function gitTrackedFiles(paths: string[]): string[] {
  const output = execFileSync("git", ["ls-files", "--", ...paths], {
    cwd: repositoryRoot,
    encoding: "utf8",
  });
  return output.split("\n").filter((line) => line.length > 0);
}

function isExcluded(path: string): boolean {
  if (isLegacyScientificSvg(path)) {
    return true;
  }
  if (excludedReleasePaths.has(path)) {
    return true;
  }
  for (const prefix of intentionalReleaseExclusions.keys()) {
    if (path.startsWith(prefix)) {
      return true;
    }
  }
  return false;
}

function isPublished(path: string): boolean {
  if (isExcluded(path)) {
    return false;
  }
  if (fileAllowlist.includes(path)) {
    return true;
  }
  return directoryAllowlist.some((entry) => path.startsWith(`${entry}/`));
}

function isIntentionallyExcluded(path: string): boolean {
  if (isLegacyScientificSvg(path)) {
    return true;
  }
  for (const prefix of intentionalReleaseExclusions.keys()) {
    if (path.startsWith(prefix)) {
      return true;
    }
  }
  return false;
}

async function collectFiles(root: string, prefix: string): Promise<string[]> {
  const entries = await readdir(root, { withFileTypes: true });
  const files: string[] = [];
  for (const entry of entries) {
    const path = prefix === "" ? entry.name : `${prefix}/${entry.name}`;
    if (entry.isDirectory()) {
      files.push(...(await collectFiles(join(root, entry.name), path)));
    } else if (entry.isFile()) {
      files.push(path);
    }
  }
  return files;
}

async function livingReportCopiesReachableByAllowlist(): Promise<string[]> {
  const copies = new Set<string>();
  for (const entry of fileAllowlist) {
    if (entry.endsWith(`/${livingReportPdf}`)) {
      copies.add(entry);
    }
  }
  for (const entry of directoryAllowlist) {
    const root = join(repositoryRoot, entry);
    if (!existsSync(root)) {
      continue;
    }
    for (const file of await collectFiles(root, entry)) {
      if (file.endsWith(`/${livingReportPdf}`)) {
        copies.add(file);
      }
    }
  }
  return [...copies].sort();
}

describe("curated release allowlist completeness", () => {
  const workspaces: string[] = [];
  let destination: string;
  let result: ReleaseBuildResult;

  afterAll(async () => {
    await Promise.all(
      workspaces.map((workspace) =>
        rm(workspace, { recursive: true, force: true }),
      ),
    );
  });

  beforeAll(async () => {
    const workspace = await mkdtemp(
      join(tmpdir(), "aidd-allowlist-completeness-"),
    );
    workspaces.push(workspace);
    destination = join(workspace, "public-release");
    result = await buildPublicRelease({
      sourceRoot: repositoryRoot,
      destination,
      inventoryPath: join(workspace, "inventory.txt"),
    });
  }, 30_000);

  it("names only files that exist in the repository", () => {
    const missing = fileAllowlist.filter(
      (entry) => !existsSync(join(repositoryRoot, entry)),
    );

    expect(missing).toEqual([]);
  });

  it("ships the scripts invoked by the site build and figure checks", async () => {
    for (const path of [
      "site/scripts/make-site-figures.py",
      "site/scripts/check-site-figures.py",
    ]) {
      await expect(access(join(destination, path))).resolves.toBeUndefined();
    }
  });

  it.skipIf(!isGitCheckout)(
    "publishes every tracked lab and report file or records why it stays behind",
    () => {
      const tracked = gitTrackedFiles(["labs", "report"]).filter((path) => {
        if (path.startsWith("report/")) {
          return true;
        }
        if (!path.startsWith("labs/")) {
          return false;
        }
        const parts = path.split("/");
        if (parts.length < 3) {
          return false;
        }
        return parts[1] !== "src" && parts[1] !== "tests";
      });
      const unpublished = tracked.filter(
        (path) => !isPublished(path) && !isIntentionallyExcluded(path),
      );
      expect(unpublished).toEqual([]);
      // A repository initialized from the curated tree contains no withheld
      // files. Its public allowlist still needs the same exclusion rules.
      for (const reason of intentionalReleaseExclusions.values()) {
        expect(reason.length).toBeGreaterThan(0);
      }
    },
  );

  it("keeps the reader-trial answer sheets out of the release", async () => {
    for (const path of answerSheets) {
      expect(excludedReleasePaths.has(path)).toBe(true);
    }
    expect(excludedReleasePaths.has(blankObservationForm)).toBe(false);

    const source = await mkdtemp(join(tmpdir(), "aidd-reader-trial-source-"));
    workspaces.push(source);
    for (const path of [...answerSheets, blankObservationForm]) {
      await mkdir(dirname(join(source, path)), { recursive: true });
      await writeFile(join(source, path), "Facilitator material.\n");
    }
    const workspace = await mkdtemp(join(tmpdir(), "aidd-reader-trial-out-"));
    workspaces.push(workspace);
    const release = join(workspace, "public-release");
    const built = await buildPublicRelease({
      sourceRoot: source,
      destination: release,
      inventoryPath: join(workspace, "inventory.txt"),
    });

    for (const path of answerSheets) {
      await expect(access(join(release, path))).rejects.toThrow();
      expect(built.files.map((entry) => entry.path)).not.toContain(path);
      expect(built.skipped.some((entry) => entry.startsWith(`${path} (`))).toBe(
        true,
      );
    }
    await expect(
      access(join(release, blankObservationForm)),
    ).resolves.toBeUndefined();
  });

  it("publishes the living-report PDF through exactly one allowlist route", async () => {
    const reachable = await livingReportCopiesReachableByAllowlist();
    const published = reachable.filter(isPublished);
    const fileRoutes = fileAllowlist.filter((entry) =>
      published.includes(entry),
    );
    const directoryRoutes = directoryAllowlist.filter((entry) =>
      published.some((path) => path.startsWith(`${entry}/`)),
    );

    expect(published).toHaveLength(1);
    expect(fileRoutes.length + directoryRoutes.length).toBe(1);

    const shipped = (await collectFiles(destination, "")).filter((path) =>
      path.endsWith(`/${livingReportPdf}`),
    );
    expect(shipped).toEqual(published);
  });
});
