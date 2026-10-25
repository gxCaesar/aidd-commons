import { execFile as execFileCallback } from "node:child_process";
import { mkdtemp, readFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { promisify } from "node:util";
import { fileURLToPath } from "node:url";

import { describe, expect, it } from "vitest";

import type { ComparisonSystem } from "../../catalog/schema/comparison.js";
import { loadComparisonSystems } from "../../scripts/comparisons/comparisons.js";
import {
  buildComparisonExport,
  buildPublicationRecord,
  loadPublicationMetadata,
  renderComparisonAudit,
} from "../../scripts/comparisons/export.js";
import { loadComparisonTaxonomy } from "../../scripts/comparisons/taxonomy.js";
import { latestCurrentCalendarDate } from "../../catalog/schema/resource.js";

const execFile = promisify(execFileCallback);
const repositoryRoot = fileURLToPath(new URL("../..", import.meta.url));
const tsxCli = new URL("../../node_modules/tsx/dist/cli.mjs", import.meta.url);

type CommandResult = {
  exitCode: number;
  stderr: string;
  stdout: string;
};

async function runExporter(
  root: string,
  extraArguments: string[] = [],
): Promise<CommandResult> {
  try {
    const { stderr, stdout } = await execFile(
      process.execPath,
      [
        tsxCli.pathname,
        "scripts/comparisons/export.ts",
        "--output",
        join(root, "data"),
        "--audit",
        join(root, "COMPARISON_AUDIT.md"),
        "--today",
        latestCurrentCalendarDate(),
        ...extraArguments,
      ],
      { cwd: repositoryRoot },
    );
    return { exitCode: 0, stderr, stdout };
  } catch (error) {
    const commandError = error as {
      code?: number;
      stderr?: string;
      stdout?: string;
    };
    return {
      exitCode: commandError.code ?? 1,
      stderr: commandError.stderr ?? "",
      stdout: commandError.stdout ?? "",
    };
  }
}

async function readOutputs(root: string): Promise<[string, string, string]> {
  return Promise.all([
    readFile(join(root, "data/comparison.v1.json"), "utf8"),
    readFile(join(root, "data/comparison.v1.csv"), "utf8"),
    readFile(join(root, "COMPARISON_AUDIT.md"), "utf8"),
  ]);
}

describe("comparison export CLI", () => {
  // The test runs the exporter twice and compares the two runs byte for byte.
  // Each run takes about two seconds on an idle machine, and the whole file
  // has to fit the default five-second budget with the rest of the suite
  // running beside it, so the budget is stated rather than assumed.
  it("writes deterministic matrix, bounds, and the frozen depth tranche", { timeout: 60_000 }, async () => {
    const firstRoot = await mkdtemp(join(tmpdir(), "aidd-comparison-first-"));
    const secondRoot = await mkdtemp(join(tmpdir(), "aidd-comparison-second-"));

    const firstRun = await runExporter(firstRoot);
    expect(firstRun).toMatchObject({ exitCode: 0, stderr: "" });
    expect(firstRun.stdout).toContain("Exported 1209 comparison cells.");

    const firstOutputs = await readOutputs(firstRoot);
    const payload = JSON.parse(firstOutputs[0]) as {
      claims: {
        most_comprehensive: { status: string };
        most_detailed: { status: string };
      };
      gaps: {
        candidates: Array<{ self_depth: string }>;
        executable_candidates: Array<{ self_depth: string; topic_id: string }>;
        selected_depth_candidates: Array<{
          implementation: { status: string };
          topic_id: string;
        }>;
        selection_status: string;
        self_audit_needed: Array<{ self_depth: string }>;
      };
      observations: {
        default_unverified_cells: number;
        direct_cells: number;
        total_cells: number;
      };
      providers: Array<{
        access: Record<string, { evidence?: string[] }>;
        evidence: Array<{ evidence_id: string }>;
        licenses: Array<{ evidence: string[] }>;
      }>;
      rows: Array<{
        evidence: Array<{
          repository_path?: string;
          source_type: string;
          url?: string;
        }>;
      }>;
      summaries: Array<{ absent_cells: number }>;
    };

    expect(payload.rows).toHaveLength(1209);
    // Thirteen providers at five thresholds: 'executable-on-real-data' was added on
    // 2026-09-11 so a checker over authored inputs stops counting like a pipeline.
    expect(payload.summaries).toHaveLength(65);
    // Direct cells rise as external providers are actually reviewed; the sum
    // must always close against the materialized matrix.
    expect(
      payload.observations.direct_cells +
        payload.observations.default_unverified_cells,
    ).toBe(payload.observations.total_cells);
    // Rose from 328 direct on 2026-09-11 as every thin provider was surveyed against
    // its declared surfaces. The denominator must stay closed.
    expect(payload.observations).toEqual({
      default_unverified_cells: 618,
      direct_cells: 591,
      total_cells: 1209,
    });
    expect(payload.claims).toMatchObject({
      most_comprehensive: { status: "not_established" },
      most_detailed: { status: "not_established" },
    });
    expect(
      payload.gaps.selected_depth_candidates.map(({ topic_id }) => topic_id),
    ).toEqual([
      "t05-small-molecule-representation",
      "t11-physical-model-system-state",
      "t15-experiment-pool-budget-feasibility",
    ]);
    expect(payload.gaps.selection_status).toBe("frozen_three_candidates");
    expect(
      payload.gaps.selected_depth_candidates.map(
        ({ implementation }) => implementation.status,
      ),
    ).toEqual(["completed", "completed", "completed"]);
    expect(
      payload.gaps.candidates.every(
        ({ self_depth }) => self_depth !== "unverified",
      ),
    ).toBe(true);
    expect(
      payload.gaps.self_audit_needed.every(
        ({ self_depth }) => self_depth === "unverified",
      ),
    ).toBe(true);
    for (const provider of payload.providers) {
      const evidenceIds = new Set(
        provider.evidence.map(({ evidence_id }) => evidence_id),
      );
      for (const claim of Object.values(provider.access)) {
        for (const evidenceId of claim.evidence ?? []) {
          expect(evidenceIds.has(evidenceId)).toBe(true);
        }
      }
      for (const license of provider.licenses) {
        for (const evidenceId of license.evidence) {
          expect(evidenceIds.has(evidenceId)).toBe(true);
        }
      }
    }
    expect(
      payload.rows.some(({ evidence }) =>
        evidence.some(
          (source) =>
            source.source_type === "repository_path" &&
            source.repository_path ===
              "site/src/content/docs/learn/foundations/getting-started.mdx" &&
            source.url === undefined,
        ),
      ),
    ).toBe(true);
    expect(firstOutputs[1].trimEnd().split("\n")).toHaveLength(1210);
    expect(firstOutputs[2]).toContain("Claim status: not established");
    // A comparator's ceiling falls whenever this project reviews a cell and finds
    // it below the threshold, by recorded absence or by shallow depth. Both are
    // ceilings lowered by our own review, so the audit publishes the counterfactual
    // beside the result. As of 2026-09-11 the bound condition passes ONLY because
    // of that review: without it the strongest external upper bound equals this
    // project's own lower bound and criterion 5 fails. If this ever reads a number
    // below 93, the lead has become independent of our own reviewing.
    expect(firstOutputs[2]).toContain(
      "Comparator ceilings at 'explained' were lowered by",
    );
    expect(firstOutputs[2]).toContain(
      "Had none of them been reviewed, the strongest external upper bound would be 93.",
    );
    expect(
      payload.summaries.every((summary) => summary.absent_cells >= 0),
    ).toBe(true);
    expect(firstOutputs[2]).toContain("Confirmed depth gaps");
    // Was 0 until external providers were reviewed topic by topic, rose as review
    // found real gaps, and returned to 0 on 2026-09-10 when the last one was
    // closed by building it. It rose to 1 on 2026-09-11 when the independent
    // second reading lowered construct definition below 'worked', then returned
    // to 0 later that day when a new lesson gave that topic its own worked case,
    // confirmed by a fifth independent-reading batch. A gap needs direct evidence
    // on both sides, so this count moves only with real review or real teaching,
    // never on its own.
    expect(firstOutputs[2]).toContain(
      "0 confirmed depth gaps have direct AIDD Commons evidence",
    );
    // Markdown column widths follow the widest row, so compare on collapsed
    // whitespace rather than on the padded table text.
    const auditRows = firstOutputs[2].replace(/[ \t]+/g, " ");
    expect(auditRows).toContain("No evidence-backed gap identified");
    expect(auditRows).not.toContain(
      "| biologics-design | t13-biologic-modality-construct |",
    );
    expect(firstOutputs[1].split("\n")[0]).toContain(",depth,run_basis,");
    expect(auditRows).toContain("| Executable on real data |");
    expect(firstOutputs[2]).toContain(
      "## Independent second reading of this project's row",
    );
    expect(firstOutputs[2]).toContain(
      "External provider records have not been re-surveyed since 2026-09-11.",
    );
    expect(firstOutputs[2]).toContain("It is shallower on 0");
    // The structure rows left the executable queue on 2026-09-11 when deposited
    // EGFR structures entered the repository and a second independent reading of
    // the new lab confirmed them. The two physics rows left it later that day
    // when a new observable-and-convergence lab over the real rMD17 trajectories
    // did the same, confirmed by a sixth independent-reading batch run with the
    // real data files present. What remains needs authored or new real data, or
    // rows the second reading lowered.
    for (const topic of [
      "| structure-and-pockets | t10-binding-site-pocket-definition |",
      "| structure-and-pockets | t10-structure-evidence-state |",
      "| dti-screening | t09-binding-mode-pose-hypothesis |",
      "| representations | t05-complex-interaction-representation |",
      "| physics-based-modeling | t11-dynamic-simulation-observable |",
      "| physics-based-modeling | t11-convergence-protocol-uncertainty |",
    ]) {
      expect(auditRows).not.toContain(topic);
    }
    expect(auditRows).not.toContain(
      "| molecular-generation | t12-candidate-design-space |",
    );
    expect(auditRows).not.toContain(
      "| physics-based-modeling | t11-docking-scoring-protocol |",
    );
    expect(auditRows).not.toContain(
      "| qsar-properties | t07-interpretability-sar |",
    );
    expect(auditRows).not.toContain(
      "| dti-screening | t09-binder-classification |",
    );
    // Design objectives and the validity funnel left this table on 2026-09-10 when
    // the generation gate lab made both runnable here.
    expect(auditRows).not.toContain(
      "| molecular-generation | t12-design-objective-constraints |",
    );
    expect(auditRows).not.toContain(
      "| molecular-generation | t12-validity-novelty-synthetic-screen |",
    );
    // Closed by the offline contract inspector on 2026-09-10.
    expect(auditRows).not.toContain(
      "| qsar-properties | t07-endpoint-definition |",
    );
    // The worked threshold cannot see a topic where this project is at 'worked'
    // and a provider is already runnable, so that deficit gets its own table.
    // Was 6 on 2026-09-11, then closed one by one as each gap got a real lab
    // and a fresh independent reading: metabolism/DDI risk, PK exposure
    // endpoints (partially, clearance only), and omics-and-perturbation
    // representation on 2026-09-12, the last of the six, closed it to 0.
    // It reopened on 2026-10-23 for one topic: the thirty-fifth independent
    // reading found that the runnable profile check validates the local
    // PaperQA configuration and not a tool's input and output contract, so
    // the self record was lowered from 'executable' to 'worked' and this
    // project fell below two external providers that are already runnable
    // there. A new laboratory and the thirty-ninth reading closed it again.
    // The gate names every topic in the list, so a reopened gap cannot pass
    // unnoticed, and it also checks that the table says so when there is
    // none, so an empty list is not reported as an empty table.
    expect(firstOutputs[2]).toContain("## Confirmed executable gaps");
    expect(payload.gaps.executable_candidates.map((gap) => gap.topic_id)).toEqual([]);
    expect(auditRows).toContain("No evidence-backed executable gap identified");
    expect(firstOutputs[2]).toContain(
      `${payload.gaps.executable_candidates.length} topics are below 'executable' here`,
    );
    expect(firstOutputs[2]).toContain(
      "Self-audit needed before gap classification",
    );
    expect(firstOutputs[2]).toContain("Frozen v0.2b depth candidates");
    expect(firstOutputs[2]).toContain("Small-molecule representations");
    expect(firstOutputs[2]).toContain("completed");
    expect(firstOutputs[2]).not.toContain("No v0.2b candidate selected");
    expect(firstOutputs.join("\n")).not.toMatch(
      /overall_score|weighted_score/iu,
    );

    const secondRun = await runExporter(secondRoot);
    expect(secondRun).toMatchObject({ exitCode: 0, stderr: "" });
    expect(await readOutputs(secondRoot)).toEqual(firstOutputs);
  });
});

describe("public correction window", () => {
  const fixtureRoot = "tests/comparisons/fixtures";
  const firstPublishedAt = "2026-10-25T02:33:00Z";
  const endsAt = "2026-11-24T02:33:00.000Z";
  const publicationTime = new Date(firstPublishedAt);

  it("keeps an unrecorded publication explicit without starting a window", () => {
    expect(buildPublicationRecord(undefined, publicationTime)).toMatchObject({
      correction_url: null,
      correction_window_days: 30,
      correction_window_ends_at: null,
      correction_window_status: "not_recorded",
      first_published_at: null,
      repository_url: null,
      site_url: null,
      status_checked_on: null,
    });
  });

  it("accepts a complete publication record and counts thirty full days", async () => {
    const metadata = await loadPublicationMetadata(
      `${fixtureRoot}/valid-publication.json`,
      { now: publicationTime },
    );
    const beforeEnd = buildPublicationRecord(
      metadata,
      new Date("2026-11-24T02:32:59.999Z"),
    );
    expect(beforeEnd).toMatchObject({
      correction_window_ends_at: endsAt,
      correction_window_status: "open",
      first_published_at: firstPublishedAt,
      status_checked_on: "2026-11-24",
    });
    expect(
      buildPublicationRecord(metadata, new Date(endsAt))
        .correction_window_status,
    ).toBe("elapsed");
    // Same-day rebuilds carry the date of the check, not a varying timestamp.
    expect(buildPublicationRecord(metadata, publicationTime)).toEqual(
      buildPublicationRecord(metadata, new Date("2026-10-25T23:59:59Z")),
    );
  });

  it.each([
    ["bad-publication-without-correction.json", "correction_url"],
    ["bad-publication-short-window.json", "correction_window_days"],
    ["bad-publication-future.json", "first_published_at cannot be later"],
  ])(
    "rejects %s with the affected field in its diagnostic",
    async (fixture, diagnostic) => {
      await expect(
        loadPublicationMetadata(`${fixtureRoot}/${fixture}`, {
          now: publicationTime,
        }),
      ).rejects.toThrow(diagnostic);
    },
  );

  it("requires an actual UTC timestamp and HTTPS correction route", async () => {
    const metadata = await loadPublicationMetadata(
      `${fixtureRoot}/valid-publication.json`,
      { now: publicationTime },
    );
    for (const first_published_at of [
      "2026-02-30T00:00:00Z",
      "2026-10-25",
      "2026-10-25T10:33:00+08:00",
    ]) {
      expect(() =>
        buildPublicationRecord(
          { ...metadata, first_published_at },
          publicationTime,
        ),
      ).toThrow("first_published_at");
    }
    expect(() =>
      buildPublicationRecord(
        { ...metadata, correction_url: "http://example.org/correction" },
        publicationTime,
      ),
    ).toThrow("correction_url");
  });

  it("never promotes a claim or changes the frozen audit when a window elapses", async () => {
    const [systems, taxonomy, publication] = await Promise.all([
      loadComparisonSystems("catalog/comparisons/systems"),
      loadComparisonTaxonomy("catalog/comparisons/taxonomy.yaml"),
      loadPublicationMetadata(`${fixtureRoot}/valid-publication.json`, {
        now: publicationTime,
      }),
    ]);
    const baseline = buildComparisonExport(systems, taxonomy);
    const elapsed = buildComparisonExport(systems, taxonomy, undefined, [], {
      publication,
      now: new Date(endsAt),
    });
    expect(elapsed.claims.most_comprehensive).toMatchObject({
      correction_window_status: "elapsed",
      status: "not_established",
    });
    expect(elapsed.claims.most_detailed.status).toBe("not_established");
    expect(elapsed.rows).toEqual(baseline.rows);
    expect(elapsed.summaries).toEqual(baseline.summaries);
    expect(elapsed.as_of).toBe(baseline.as_of);
    const audit = await renderComparisonAudit(elapsed);
    expect(audit).toContain("Claim status: not established");
    expect(audit).toContain("its status was elapsed");
    expect(audit).toContain(
      "Elapsed time alone does not establish either claim",
    );
    expect(audit).toContain(publication.correction_url);
    expect(audit).not.toContain(
      "No public correction window has been recorded",
    );
  });

  it(
    "loads the explicit publication record through the CLI",
    { timeout: 60_000 },
    async () => {
      const root = await mkdtemp(join(tmpdir(), "aidd-publication-"));
      const result = await runExporter(root, [
        "--publication",
        `${fixtureRoot}/valid-publication.json`,
        "--now",
        firstPublishedAt,
      ]);
      expect(result).toMatchObject({ exitCode: 0, stderr: "" });
      const [json, , audit] = await readOutputs(root);
      expect(JSON.parse(json)).toMatchObject({
        claims: {
          most_comprehensive: {
            correction_window_status: "open",
            status: "not_established",
          },
          most_detailed: { status: "not_established" },
        },
        publication: {
          first_published_at: firstPublishedAt,
          correction_window_ends_at: endsAt,
          correction_window_status: "open",
        },
      });
      expect(audit).toContain("its status was open");
    },
  );
});

describe("most detailed bound condition", () => {
  const depthOrder = [
    "absent",
    "mentioned",
    "explained",
    "worked",
    "executable",
    "assessed",
  ];

  async function committedRecords() {
    const [systems, taxonomy] = await Promise.all([
      loadComparisonSystems("catalog/comparisons/systems"),
      loadComparisonTaxonomy("catalog/comparisons/taxonomy.yaml"),
    ]);
    return { systems, taxonomy };
  }

  function withSelf(
    systems: ComparisonSystem[],
    edit: (self: ComparisonSystem) => void,
  ): ComparisonSystem[] {
    const copy = structuredClone(systems);
    edit(copy.find(({ id }) => id === "aidd-commons")!);
    return copy;
  }

  function atWorked(self: ComparisonSystem, count: number) {
    // Raise every self cell below 'worked' to 'worked', then lower `count`
    // worked cells back to 'explained'. Evidence is kept, so only depth moves.
    for (const cell of self.coverage) {
      if (depthOrder.indexOf(cell.depth) < depthOrder.indexOf("worked")) {
        cell.depth = "worked";
      }
    }
    self.coverage
      .filter(({ depth }) => depth === "worked")
      .slice(0, count)
      .forEach((cell) => {
        cell.depth = "explained";
      });
  }

  it("reports the committed state by the gate's own rule", async () => {
    const { systems, taxonomy } = await committedRecords();
    const detailed = buildComparisonExport(systems, taxonomy).claims
      .most_detailed;
    expect(detailed.bound_condition_satisfied).toBe(
      detailed.executable_or_assessed_self_tracks >=
        detailed.required_self_tracks &&
        detailed.self_lower_at_worked >
          detailed.strongest_external_upper_at_worked,
    );
  });

  it("needs a strict lead over every comparator and enough runnable tracks", async () => {
    const { systems, taxonomy } = await committedRecords();
    const externalUpper = buildComparisonExport(systems, taxonomy).claims
      .most_detailed.strongest_external_upper_at_worked;
    const total = taxonomy.tracks.flatMap(({ topics }) => topics).length;

    const leads = buildComparisonExport(
      withSelf(systems, (self) => atWorked(self, total - externalUpper - 1)),
      taxonomy,
    ).claims.most_detailed;
    expect(leads.self_lower_at_worked).toBe(externalUpper + 1);
    expect(leads.bound_condition_satisfied).toBe(true);

    // A tie with the strongest comparator is not a lead.
    const ties = buildComparisonExport(
      withSelf(systems, (self) => atWorked(self, total - externalUpper)),
      taxonomy,
    ).claims.most_detailed;
    expect(ties.self_lower_at_worked).toBe(externalUpper);
    expect(ties.bound_condition_satisfied).toBe(false);

    // Leading at 'worked' is not enough without runnable or assessed tracks.
    const shallow = buildComparisonExport(
      withSelf(systems, (self) => {
        atWorked(self, total - externalUpper - 1);
        for (const cell of self.coverage) {
          if (cell.depth === "executable" || cell.depth === "assessed") {
            cell.depth = "worked";
            delete cell.run_basis;
          }
        }
      }),
      taxonomy,
    ).claims.most_detailed;
    expect(shallow.executable_or_assessed_self_tracks).toBe(0);
    expect(shallow.bound_condition_satisfied).toBe(false);
  });
});
