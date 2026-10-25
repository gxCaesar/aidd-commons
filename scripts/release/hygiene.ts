import { mkdir, readdir, readFile, writeFile } from "node:fs/promises";
import { basename, dirname, join, relative, resolve, sep } from "node:path";

export type HygieneFinding = {
  detail: string;
  path: string;
  rule: string;
};

// The legacy citation path remains public, but only as this compatibility page.
// Keeping the text shared with the builder makes curated-source re-exports stable.
export const roadmapCompatibilityPath = "docs/ROADMAP_V0.2.md";
export const publicRoadmapPath = "docs/PUBLIC_ROADMAP.md";
export const publicRoadmapPointer = `# Public roadmap compatibility link

Public milestones and limitations are maintained in [PUBLIC_ROADMAP.md](PUBLIC_ROADMAP.md).
This compatibility page preserves existing citation paths.

- [rMD17 system-state results](PUBLIC_ROADMAP.md#rmd17-system-state).
- [PK source screening on 2026-09-12](PUBLIC_ROADMAP.md#pk-source-screening-2026-09-12).
`;

const forbiddenControlDirectories = new Set([
  ".agents",
  ".codex",
  ".git",
  ".superpowers",
]);

const forbiddenFileNames = new Set([
  "agents.md",
  "claude.md",
  "claude-codex-workflow-log.md",
]);
const lockfileNames = new Set([
  "bun.lock",
  "bun.lockb",
  "composer.lock",
  "package-lock.json",
  "pnpm-lock.yaml",
  "poetry.lock",
  "uv.lock",
  "yarn.lock",
]);

const checksumMetadataPattern =
  /(?:["']\s*)?\b(?:(?:[a-z0-9]+[_-])*(?:sha(?:1|224|256|384|512)|md5|checksums?|digests?)(?:[_-][a-z0-9]+)*|integrity)\b(?:\s*["'])?\s*[:=]/iu;
const credentialPattern =
  /(?:^|\n)\s*(?:[A-Z][A-Z0-9_]*(?:TOKEN|SECRET|PASSWORD|API_KEY|ACCESS_KEY)|(?:api[_-]?key|token|secret|password))\s*[:=]/iu;
const agentInstructionPattern =
  /(?:^|\n)\s*(?:#{1,6}\s*)?(?:local\s+)?agent\s+instructions?\b|\byou\s+are\s+an\s+(?:AI\s+)?agent\b/iu;
const internalTaskReportPattern =
  /\btask\s+\d+\s+(?:implementer|review|fix|license\s+fix)\s+report\b/iu;
const approvalReceiptPattern = /\bapproval\s+receipt\b/iu;
const absoluteUserPathPattern = /\/Users\/[A-Za-z0-9._-]+(?:\/[^\s"']*)?/u;
const internalMarkdownVisibilityPattern =
  /^\s*(?:<!--\s*)?(?:#{1,6}\s*)?visibility\s*:\s*internal\b/imu;
const pipelineStateKeys = new Set([
  "activity_id",
  "activity_ids",
  "canonical_smiles",
  "command",
  "descriptor_preprocessor_fit_ids",
  "evaluation_command",
  "feature_fit_ids",
  "fit_trace",
  "grouping_keys",
  "ids",
  "member_id",
  "member_ids",
  "membership",
  "model_fit_ids",
  "molecule_chembl_id",
  "parsed_rows",
  "parent_molecule_chembl_id",
  "planned_test_evaluation_command",
  "pretest_passed",
  "pipeline_status",
  "raw_row",
  "raw_rows",
  "prediction",
  "predictions",
  "run_status",
  "smiles",
  "test_evaluation_complete",
  "test_evaluation_started",
  "target_pchembl",
]);

// Reviewed public teaching files whose content trips a rule written for a different
// risk. The pipeline-state keys exist to stop locked-evaluation rows and membership
// leaving the repository; these datasets are authored by hand, declare so in their
// own provenance field, and are already served as site downloads.
// Each exemption covers one rule at one path, and for pipeline-state content one
// key, so any other finding in the same file still fails the scan.
type ReviewedExemption = {
  key?: string;
  path: string;
  rule: "pipeline-state-content";
};

const reviewedExemptions: ReviewedExemption[] = [
  ...[
    "labs/binder_definition/dataset.json",
    "labs/design_space/spaces.json",
    "labs/generation_gate/candidates.json",
    "labs/safety_evidence/dataset.json",
    "labs/sar_attribution/dataset.json",
  ].map(
    (path): ReviewedExemption => ({
      key: "smiles",
      path,
      rule: "pipeline-state-content",
    }),
  ),
  {
    key: "parent_molecule_chembl_id",
    path: "labs/cyp_assay_system/summary.json",
    rule: "pipeline-state-content",
  },
  {
    key: "parent_molecule_chembl_id",
    path: "labs/az_clearance_system/summary.json",
    rule: "pipeline-state-content",
  },
  // The decision-unit lab reports how a declared cohort of compounds resolves
  // to its parent molecules, and shows one reported measurement with its
  // activity identifier. Those identifiers are the teaching content of the
  // lab, not a record of which rows a model was fitted on.
  {
    key: "parent_molecule_chembl_id",
    path: "labs/decision_unit_scope/summary.json",
    rule: "pipeline-state-content",
  },
  {
    key: "activity_id",
    path: "labs/decision_unit_scope/summary.json",
    rule: "pipeline-state-content",
  },
  {
    key: "molecule_chembl_id",
    path: "labs/decision_unit_scope/summary.json",
    rule: "pipeline-state-content",
  },
  {
    key: "parent_molecule_chembl_id",
    path: "labs/decision_unit_scope/protocol.json",
    rule: "pipeline-state-content",
  },
  {
    key: "molecule_chembl_id",
    path: "labs/decision_unit_scope/protocol.json",
    rule: "pipeline-state-content",
  },
  {
    key: "activity_id",
    path: "labs/decision_unit_scope/protocol.json",
    rule: "pipeline-state-content",
  },
  {
    key: "molecule_chembl_id",
    path: "labs/split_leakage_audit/protocol.json",
    rule: "pipeline-state-content",
  },
  {
    key: "molecule_chembl_id",
    path: "labs/multi_endpoint_tradeoff/protocol.json",
    rule: "pipeline-state-content",
  },
  {
    key: "parent_molecule_chembl_id",
    path: "labs/multi_endpoint_tradeoff/summary.json",
    rule: "pipeline-state-content",
  },
  {
    key: "molecule_chembl_id",
    path: "labs/entity_glossary_audit/protocol.json",
    rule: "pipeline-state-content",
  },
  {
    key: "molecule_chembl_id",
    path: "labs/generalization_unit_audit/protocol.json",
    rule: "pipeline-state-content",
  },
  {
    key: "membership",
    path: "labs/generalization_unit_audit/protocol.json",
    rule: "pipeline-state-content",
  },
  {
    key: "membership",
    path: "labs/generalization_unit_audit/summary.json",
    rule: "pipeline-state-content",
  },
  {
    key: "molecule_chembl_id",
    path: "labs/nomination_readiness_audit/protocol.json",
    rule: "pipeline-state-content",
  },
  {
    key: "parent_molecule_chembl_id",
    path: "labs/nomination_readiness_audit/summary.json",
    rule: "pipeline-state-content",
  },
];

function isExempt(path: string, rule: string, key?: string): boolean {
  return reviewedExemptions.some(
    (exemption) =>
      exemption.path === path &&
      exemption.rule === rule &&
      exemption.key === key,
  );
}

function portablePath(root: string, path: string): string {
  const value = relative(root, path).split(sep).join("/");
  return value === "" ? "." : value;
}

function addFinding(
  findings: HygieneFinding[],
  path: string,
  rule: string,
  detail: string,
): void {
  findings.push({ detail, path, rule });
}

function scanPathName(
  findings: HygieneFinding[],
  path: string,
  name: string,
  isDirectory: boolean,
): boolean {
  const lowerName = name.toLowerCase();

  if (isDirectory && forbiddenControlDirectories.has(lowerName)) {
    addFinding(
      findings,
      path,
      "private-control-directory",
      "private control directory",
    );
    return true;
  }
  if (isDirectory && (lowerName === "prompt" || lowerName === "prompts")) {
    addFinding(findings, path, "private-prompt", "private prompt directory");
    return true;
  }

  // macOS writes filesystem metadata into any tree it touches: .DS_Store holds
  // directory view state, ._name files hold AppleDouble resource forks, and a
  // zip round trip creates a __MACOSX directory full of forks. None of it
  // belongs in a public release, so the directory is pruned on the first hit
  // and its binary content is never read as text.
  if (lowerName === "__macosx") {
    addFinding(
      findings,
      path,
      "macos-metadata",
      "macOS archive metadata path segment",
    );
    return true;
  }
  if (lowerName === ".ds_store") {
    addFinding(
      findings,
      path,
      "macos-metadata",
      "macOS directory metadata file",
    );
    return true;
  }
  if (name.startsWith("._")) {
    addFinding(
      findings,
      path,
      "macos-metadata",
      "macOS AppleDouble resource fork",
    );
    return true;
  }

  if (forbiddenFileNames.has(lowerName)) {
    addFinding(
      findings,
      path,
      "agent-instruction-file",
      "agent instruction file",
    );
  }
  if (lowerName === ".env" || lowerName.startsWith(".env.")) {
    addFinding(findings, path, "environment-file", "environment file");
  }
  if (lockfileNames.has(lowerName)) {
    addFinding(
      findings,
      path,
      "lockfile",
      "lockfile can contain integrity metadata",
    );
  }
  if (/^task-[a-z0-9._-]*report\.md$/u.test(lowerName)) {
    addFinding(
      findings,
      path,
      "internal-task-report",
      "internal task report filename",
    );
  }
  if (/^task-[a-z0-9._-]*brief\.md$/u.test(lowerName)) {
    addFinding(
      findings,
      path,
      "internal-task-brief",
      "internal task brief filename",
    );
  }
  if (/(?:^|[-_])prompt(?:[-_.]|$)/u.test(lowerName)) {
    addFinding(findings, path, "private-prompt", "private prompt filename");
  }
  if (/approval[-_ ]?receipt/u.test(lowerName)) {
    addFinding(
      findings,
      path,
      "approval-receipt",
      "private authorization filename",
    );
  }
  if (
    /^(?:locked-evaluation\.started|test-evaluation\.started|pipeline-state)\.json$/u.test(
      lowerName,
    )
  ) {
    addFinding(findings, path, "pipeline-state", "pipeline state artifact");
  }

  return false;
}

function scanText(
  findings: HygieneFinding[],
  path: string,
  text: string,
): void {
  if (/\.(?:md|mdx|markdown)$/iu.test(path)) {
    const markedInternal = internalMarkdownVisibilityPattern.test(text);
    const unconvertedCheckpoint =
      path === roadmapCompatibilityPath &&
      text.replace(/\r\n/gu, "\n") !== publicRoadmapPointer;
    if (markedInternal || unconvertedCheckpoint) {
      addFinding(
        findings,
        path,
        "internal-checkpoint-content",
        markedInternal
          ? "Markdown declares internal visibility"
          : "legacy roadmap path must contain the generated public compatibility pointer",
      );
    }
  }
  if (agentInstructionPattern.test(text)) {
    addFinding(
      findings,
      path,
      "agent-instruction-content",
      "agent instruction content",
    );
  }
  if (internalTaskReportPattern.test(text)) {
    addFinding(
      findings,
      path,
      "internal-task-report",
      "internal task report content",
    );
  }
  if (credentialPattern.test(text)) {
    addFinding(
      findings,
      path,
      "credential-like-content",
      "credential-like assignment",
    );
  }
  if (checksumMetadataPattern.test(text)) {
    addFinding(
      findings,
      path,
      "checksum-metadata",
      "checksum or integrity metadata",
    );
  }
  if (approvalReceiptPattern.test(text)) {
    addFinding(
      findings,
      path,
      "approval-receipt",
      "private authorization content",
    );
  }
  if (absoluteUserPathPattern.test(text)) {
    addFinding(findings, path, "absolute-user-path", "absolute user path");
  }
}

function scanPipelineStateContent(
  findings: HygieneFinding[],
  path: string,
  text: string,
): void {
  if (!path.toLowerCase().endsWith(".json")) {
    return;
  }

  let payload: unknown;
  try {
    payload = JSON.parse(text) as unknown;
  } catch {
    return;
  }

  function visit(value: unknown): void {
    if (Array.isArray(value)) {
      for (const item of value) {
        visit(item);
      }
      return;
    }
    if (value === null || typeof value !== "object") {
      return;
    }

    for (const [key, item] of Object.entries(value)) {
      const normalizedKey = key.toLowerCase();
      if (
        pipelineStateKeys.has(normalizedKey) &&
        !isExempt(path, "pipeline-state-content", normalizedKey)
      ) {
        addFinding(
          findings,
          path,
          "pipeline-state-content",
          `pipeline state key: ${normalizedKey}`,
        );
      }
      visit(item);
    }
  }

  visit(payload);
}

async function scanDirectory(
  root: string,
  directory: string,
  findings: HygieneFinding[],
): Promise<void> {
  const entries = await readdir(directory, { withFileTypes: true });

  for (const entry of entries) {
    const entryPath = join(directory, entry.name);
    const path = portablePath(root, entryPath);

    if (entry.isSymbolicLink()) {
      addFinding(
        findings,
        path,
        "symbolic-link",
        "symbolic links are not public release files",
      );
      continue;
    }

    if (scanPathName(findings, path, entry.name, entry.isDirectory())) {
      continue;
    }

    if (entry.isDirectory()) {
      await scanDirectory(root, entryPath, findings);
      continue;
    }

    if (!entry.isFile()) {
      addFinding(findings, path, "unsupported-file-type", "not a regular file");
      continue;
    }

    const text = await readFile(entryPath, "utf8");
    scanText(findings, path, text);
    scanPipelineStateContent(findings, path, text);
  }
}

// The curated export ships the release test suite, including the known-bad
// fixtures that exist precisely to break these rules on purpose. Those files
// are evidence that the gates work, so their content findings are exempted
// rather than allowed to fail the scan. The file-name rules still apply to
// them, so a stray environment file or a locked file inside the test tree is
// still rejected.
const knownBadFixtureDirectory = "tests/release/fixtures/known-bad/";
const releaseTestSuiteDirectory = "tests/release/";
const testMaterialContentRules = new Set([
  "absolute-user-path",
  "agent-instruction-content",
  "approval-receipt",
  "checksum-metadata",
  "credential-like-content",
  "internal-task-report",
]);

export function isTestMaterialFinding(finding: HygieneFinding): boolean {
  if (finding.path.startsWith(knownBadFixtureDirectory)) {
    return true;
  }
  return (
    finding.path.startsWith(releaseTestSuiteDirectory) &&
    testMaterialContentRules.has(finding.rule)
  );
}

export async function scanPublicTree(root: string): Promise<HygieneFinding[]> {
  const resolvedRoot = resolve(root);
  const findings: HygieneFinding[] = [];
  await scanDirectory(resolvedRoot, resolvedRoot, findings);
  return findings.sort((left, right) =>
    left.path < right.path
      ? -1
      : left.path > right.path
        ? 1
        : left.rule < right.rule
          ? -1
          : left.rule > right.rule
            ? 1
            : 0,
  );
}

type CliOptions = {
  report?: string;
  root: string;
};

function parseArguments(argumentsList: string[]): CliOptions {
  let report: string | undefined;
  let root = "public-release";

  for (let index = 0; index < argumentsList.length; index += 1) {
    const argument = argumentsList[index];
    if (argument === "--report") {
      report = argumentsList[index + 1];
      if (report === undefined) {
        throw new Error("--report requires a path");
      }
      index += 1;
    } else if (argument.startsWith("--")) {
      throw new Error(`Unknown option: ${argument}`);
    } else if (root === "public-release") {
      root = argument;
    } else {
      throw new Error(`Unexpected argument: ${argument}`);
    }
  }

  return { report, root };
}

async function main(): Promise<void> {
  const { report, root } = parseArguments(process.argv.slice(2));
  const scanned = await scanPublicTree(root);
  const exemptedFindings = scanned.filter(isTestMaterialFinding);
  const findings = scanned.filter((finding) => !isTestMaterialFinding(finding));
  const portableRoot = portablePath(process.cwd(), resolve(root));
  const result = {
    findings,
    exemptedFindings,
    ok: findings.length === 0,
    root: portableRoot,
  };

  if (report !== undefined) {
    await mkdir(dirname(report), { recursive: true });
    await writeFile(report, `${JSON.stringify(result, null, 2)}\n`);
  }

  if (findings.length > 0) {
    for (const finding of findings) {
      console.error(`${finding.path}: ${finding.rule} (${finding.detail})`);
    }
    process.exitCode = 1;
    return;
  }

  if (exemptedFindings.length > 0) {
    console.log(
      `${exemptedFindings.length} finding(s) came from the shipped test material and were exempted.`,
    );
  }
  console.log(`Release hygiene passed for ${portableRoot}.`);
}

const invokedAsCli =
  process.argv[1] !== undefined && basename(process.argv[1]) === "hygiene.ts";

if (invokedAsCli) {
  main().catch((error: unknown) => {
    console.error(error instanceof Error ? error.message : String(error));
    process.exitCode = 1;
  });
}
