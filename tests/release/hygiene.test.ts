import { mkdir, mkdtemp, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

import { describe, expect, it } from "vitest";

const fixturesDirectory = fileURLToPath(
  new URL("./fixtures/known-bad/", import.meta.url),
);
const repositoryRoot = fileURLToPath(new URL("../..", import.meta.url));

const forbiddenPipelineStateKeys = [
  "activity_id",
  "activity_ids",
  "canonical_smiles",
  "member_ids",
  "molecule_chembl_id",
  "parent_molecule_chembl_id",
  "predictions",
  "target_pchembl",
  "smiles",
  "raw_rows",
  "evaluation_command",
  "pretest_passed",
  "pipeline_status",
  "test_evaluation_complete",
  "fit_trace",
];

async function scan(root: string) {
  const { scanPublicTree } = await import("../../scripts/release/hygiene.js");
  return scanPublicTree(root);
}

async function findingsFor(fixture: string) {
  return scan(new URL(fixture, `file://${fixturesDirectory}/`).pathname);
}

describe("public release hygiene", () => {
  it("rejects a collaboration log even when its prose has no control markers", async () => {
    const root = await mkdtemp(join(tmpdir(), "aidd-handoff-hygiene-"));
    await writeFile(
      join(root, "claude-codex-workflow-log.md"),
      "Local note.\n",
    );
    const findings = await scan(root);
    expect(findings.map((finding) => finding.rule)).toContain(
      "agent-instruction-file",
    );
  });

  it.each([
    [
      "agent instruction filename",
      "agent-instruction-file/",
      "agent-instruction-file",
    ],
    [
      "agent instruction content",
      "agent-instruction-content/",
      "agent-instruction-content",
    ],
    ["internal task report", "internal-task-report/", "internal-task-report"],
    ["credential-like environment file", "credential-env/", "environment-file"],
    ["checksum metadata", "checksum-metadata/", "checksum-metadata"],
    [
      "download checksum metadata",
      "download-checksum-metadata/",
      "checksum-metadata",
    ],
    ["approval receipt", "approval-receipt/", "approval-receipt"],
    ["absolute user path", "absolute-user-path/", "absolute-user-path"],
    ["macOS metadata", "macos-metadata/", "macos-metadata"],
  ])("rejects a deliberate %s", async (_description, fixture, rule) => {
    const findings = await findingsFor(fixture);

    expect(findings.map((finding) => finding.rule)).toContain(rule);
  });

  it("rejects every form of macOS filesystem metadata", async () => {
    const findings = await findingsFor("macos-metadata/");

    expect(findings.map(({ path, rule }) => `${rule}: ${path}`)).toEqual([
      "macos-metadata: .DS_Store",
      "macos-metadata: ._file.txt",
      "macos-metadata: __MACOSX",
    ]);
  });

  it("allows ordinary scientific uses of agent and training", async () => {
    await expect(findingsFor("scientific-language/")).resolves.toEqual([]);
  });

  it("rejects result payload keys that expose membership or pipeline state", async () => {
    const findings = await findingsFor("pipeline-state-content/");
    const detectedKeys = findings
      .filter((finding) => finding.rule === "pipeline-state-content")
      .map((finding) => finding.detail.replace("pipeline state key: ", ""));

    expect(detectedKeys).toEqual(
      expect.arrayContaining(forbiddenPipelineStateKeys),
    );
  });

  it("rejects a locked-evaluation start marker by filename", async () => {
    const root = await mkdtemp(join(tmpdir(), "aidd-locked-marker-"));
    await writeFile(
      join(root, "locked-evaluation.started.json"),
      '{"status":"started"}\n',
    );

    const findings = await scan(root);

    expect(findings.map((finding) => finding.rule)).toContain("pipeline-state");
  });

  describe("reviewed teaching-file exemptions", () => {
    async function treeWith(path: string, payload: unknown): Promise<string> {
      const root = await mkdtemp(join(tmpdir(), "aidd-exemption-"));
      await mkdir(join(root, dirname(path)), { recursive: true });
      await writeFile(join(root, path), `${JSON.stringify(payload)}\n`);
      return root;
    }

    it("accepts a smiles key only in a reviewed authored dataset", async () => {
      const exempt = await treeWith("labs/sar_attribution/dataset.json", {
        molecules: [{ smiles: "CCO" }],
      });
      await expect(scan(exempt)).resolves.toEqual([]);

      const elsewhere = await treeWith("labs/new_lab/dataset.json", {
        molecules: [{ smiles: "CCO" }],
      });
      expect((await scan(elsewhere)).map(({ rule }) => rule)).toContain(
        "pipeline-state-content",
      );
    });

    it("accepts a parent_molecule_chembl_id key only in the reviewed CYP summary", async () => {
      const exempt = await treeWith("labs/cyp_assay_system/summary.json", {
        divergent_examples: {
          primary_selective: [{ parent_molecule_chembl_id: "CHEMBL298817" }],
        },
      });
      await expect(scan(exempt)).resolves.toEqual([]);

      const elsewhere = await treeWith("labs/new_lab/summary.json", {
        divergent_examples: {
          primary_selective: [{ parent_molecule_chembl_id: "CHEMBL298817" }],
        },
      });
      expect((await scan(elsewhere)).map(({ rule }) => rule)).toContain(
        "pipeline-state-content",
      );
    });

    it("accepts a parent_molecule_chembl_id key in the reviewed AZ clearance summary", async () => {
      const exempt = await treeWith("labs/az_clearance_system/summary.json", {
        pairs: {
          p: {
            divergent_examples: {
              primary_selective: [
                { parent_molecule_chembl_id: "CHEMBL361546" },
              ],
            },
          },
        },
      });
      await expect(scan(exempt)).resolves.toEqual([]);
    });

    it("still rejects any other pipeline-state key in a reviewed dataset", async () => {
      const root = await treeWith("labs/sar_attribution/dataset.json", {
        molecules: [{ smiles: "CCO", predictions: [1.0] }],
      });
      const findings = await scan(root);
      expect(findings.map(({ detail }) => detail)).toEqual([
        "pipeline state key: predictions",
      ]);
    });

    it("rejects checksum metadata in every public data manifest", async () => {
      const manifest = { entries: [{ sha256: "0".repeat(64) }] };
      for (const path of [
        "labs/egfr_structures/entries.json",
        "labs/chembl_egfr/entries.json",
      ]) {
        const findings = await scan(await treeWith(path, manifest));
        expect(findings.map(({ rule }) => rule)).toContain("checksum-metadata");
      }
    });

    it("accepts scientific integrity rules without mistaking them for file metadata", async () => {
      const root = await treeWith("labs/example/protocol.json", {
        integrity_rules: ["Selections are without replacement."],
        size_bytes: 307709,
        latest_revision: { revision_date: "2024-02-14" },
      });
      await expect(scan(root)).resolves.toEqual([]);
    });

    it("reports both checksum metadata and a pipeline-state key", async () => {
      const root = await treeWith("labs/egfr_structures/entries.json", {
        sha256: "0".repeat(64),
        smiles: "CCO",
      });
      expect((await scan(root)).map(({ rule }) => rule)).toEqual([
        "checksum-metadata",
        "pipeline-state-content",
      ]);
    });
  });

  it("does not reject the public scanner implementation itself", async () => {
    await expect(
      scan(join(repositoryRoot, "scripts", "release")),
    ).resolves.toEqual([]);
  });
});
