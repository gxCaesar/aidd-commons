import { mkdtemp, readFile, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { fileURLToPath } from "node:url";

import { describe, expect, it } from "vitest";

import { buildCoverage } from "../../scripts/curriculum/coverage.js";
import {
  buildComparisonExport,
  renderComparisonAudit,
} from "../../scripts/comparisons/export.js";
import { loadComparisonSystems } from "../../scripts/comparisons/comparisons.js";
import { loadDepthCandidateSet } from "../../scripts/comparisons/depth-candidates.js";
import {
  assertSecondReadings,
  loadSecondReadings,
} from "../../scripts/comparisons/second-reading.js";
import { loadComparisonTaxonomy } from "../../scripts/comparisons/taxonomy.js";

const repositoryRoot = fileURLToPath(new URL("../..", import.meta.url));

type NumberClaim = {
  name: string;
  // One capture group per value the sentence states, in order.
  pattern: RegExp;
};

const coverageClaims: NumberClaim[] = [
  {
    name: "distinct validated resource records",
    pattern: /(\d+) distinct validated resource records are in the current/,
  },
  {
    name: "validated learning systems",
    pattern: /from (\d+) validated\s+learning systems/,
  },
  {
    name: "topic units and curriculum tracks",
    pattern: /It crosses (\d+) topic units in all\s+(\d+) curriculum tracks/,
  },
  {
    name: "logical provider-topic cells",
    pattern: /producing ([\d,]+) logical provider-topic cells/,
  },
  {
    name: "direct observations and explicit-default unknowns",
    pattern:
      /Of these, (\d+) are direct observations and ([\d,]+) remain explicit-default/,
  },
  {
    name: "explained-or-deeper lower bound",
    pattern: /explained-or-deeper lower\s+bound of (\d+) topics/,
  },
  {
    name: "strongest external upper bound",
    pattern: /strongest external upper bound is\s+(\d+)/,
  },
  {
    name: "worked lower bound",
    pattern: /Its worked lower bound is (\d+)/,
  },
  {
    name: "executable or assessed self-audit tracks",
    pattern:
      /only\s+(\d+) of the required 12 tracks currently contain executable or assessed/,
  },
  {
    name: "selected depth candidates",
    pattern: /(\d+) candidates passed every v0.2b eligibility criterion/,
  },
];

const auditClaims: NumberClaim[] = [
  {
    name: "providers, tracks and topics",
    pattern:
      /The frozen audit contains (\d+) providers, (\d+) tracks, and (\d+) topics\./,
  },
  {
    name: "cells, direct observations and unknown cells",
    pattern:
      /It materializes ([\d,]+) provider-topic cells: (\d+) direct observations and (\d+) explicit-default unknown cells\./,
  },
  {
    name: "runnable coverage on real data",
    pattern: /Runnable coverage on real data is (\d+) topics here\./,
  },
  {
    name: "executable or assessed self-audit tracks",
    pattern:
      /(\d+) of the required (\d+) self-audit tracks contain executable or assessed coverage, (\d+) of them on real data/,
  },
];

function readValues(text: string, claim: NumberClaim): string[] | null {
  const match = new RegExp(claim.pattern.source, "g").exec(text);
  if (match === null) return null;
  return match.slice(1).map((value) => value.replaceAll(",", ""));
}

function compareValues(
  committed: string,
  regenerated: string,
  claim: NumberClaim,
): string | null {
  const stated = readValues(committed, claim);
  const measured = readValues(regenerated, claim);
  if (stated === null || measured === null) {
    const missing = stated === null ? "committed" : "regenerated";
    return `${claim.name}: no sentence matching ${claim.pattern.source} was found in the ${missing} document`;
  }
  if (stated.join(",") === measured.join(",")) return null;
  return `${claim.name}: committed ${stated.join(", ")}, regenerated ${measured.join(", ")}`;
}

function sectionOf(text: string, heading: string): string {
  const chunk = text
    .split(/^## /m)
    .find((part) => part.startsWith(`${heading}\n`));
  if (chunk === undefined) {
    throw new Error(`No section titled "${heading}" was found`);
  }
  return chunk;
}

function tableRows(section: string): string[] {
  return section
    .split("\n")
    .filter((line) => line.trimStart().startsWith("|"))
    .map((line) =>
      line
        .split("|")
        .map((cell) => cell.trim())
        .join("|"),
    )
    .filter((row) => !/^\|[-: |]+\|$/.test(row));
}

// The provider table states each provider's depth counts under named columns,
// so the columns are read by name rather than by position.
const providerDepthColumns = [
  "Executable",
  "Executable on real data",
  "Assessed",
];

function providerRow(audit: string, provider: string): Map<string, string> {
  const lines = audit.split("\n");
  const header = lines.find((line) => line.startsWith("| Provider"));
  if (header === undefined) {
    throw new Error("The provider table has no header row");
  }
  const row = lines.find((line) => line.startsWith(`| ${provider} `));
  if (row === undefined) {
    throw new Error(`No provider row for "${provider}" was found`);
  }
  const headings = header.split("|").map((cell) => cell.trim());
  const values = row.split("|").map((cell) => cell.trim());
  const cells = new Map<string, string>();
  headings.forEach((heading, index) => {
    if (heading !== "") cells.set(heading, values[index] ?? "");
  });
  return cells;
}

function providerDepths(audit: string, provider: string): string[] {
  const cells = providerRow(audit, provider);
  return providerDepthColumns.map((column) => {
    const value = cells.get(column);
    if (value === undefined) {
      throw new Error(`The provider table has no "${column}" column`);
    }
    return value;
  });
}

async function regenerate(): Promise<{
  audit: string;
  coverage: string;
  directory: string;
}> {
  const directory = await mkdtemp(join(tmpdir(), "aidd-generated-docs-"));
  const coverageOutput = join(directory, "COVERAGE.md");
  await buildCoverage({
    catalog: "catalog/resources",
    curriculum: "catalog/curriculum/tracks.yaml",
    output: coverageOutput,
  });

  const [systems, taxonomy, candidateSet, readings] = await Promise.all([
    loadComparisonSystems("catalog/comparisons/systems"),
    loadComparisonTaxonomy("catalog/comparisons/taxonomy.yaml"),
    loadDepthCandidateSet("catalog/comparisons/depth-candidates.yaml"),
    loadSecondReadings("catalog/comparisons/reviews"),
  ]);
  assertSecondReadings(systems, readings, taxonomy);
  const audit = await renderComparisonAudit(
    buildComparisonExport(
      systems,
      taxonomy,
      candidateSet,
      readings.map(({ reading }) => reading),
    ),
  );
  await writeFile(join(directory, "COMPARISON_AUDIT.md"), audit);

  return {
    audit,
    coverage: await readFile(coverageOutput, "utf8"),
    directory,
  };
}

describe("generated documents", () => {
  it("states the measured coverage numbers in the committed document", async () => {
    const regenerated = await regenerate();
    const committed = await readFile(
      join(repositoryRoot, "docs", "COVERAGE.md"),
      "utf8",
    );
    const drift: string[] = [];
    for (const claim of coverageClaims) {
      const difference = compareValues(committed, regenerated.coverage, claim);
      if (difference !== null) drift.push(difference);
    }
    expect(drift).toEqual([]);
  });

  it("keeps every coverage table identical to the regenerated one", async () => {
    const regenerated = await regenerate();
    const committed = await readFile(
      join(repositoryRoot, "docs", "COVERAGE.md"),
      "utf8",
    );
    for (const heading of [
      "Coverage by curriculum track",
      "Coverage by resource kind",
      "Coverage by pipeline stage",
      "Coverage by access level",
      "Evidence-state interpretation",
    ]) {
      expect(tableRows(sectionOf(committed, heading))).toEqual(
        tableRows(sectionOf(regenerated.coverage, heading)),
      );
    }
  });

  it("states the measured audit numbers in the committed document", async () => {
    const regenerated = await regenerate();
    const committed = await readFile(
      join(repositoryRoot, "docs", "COMPARISON_AUDIT.md"),
      "utf8",
    );
    const drift: string[] = [];
    for (const claim of auditClaims) {
      const difference = compareValues(committed, regenerated.audit, claim);
      if (difference !== null) drift.push(difference);
    }
    expect(drift).toEqual([]);
  });

  it("states this project's executable, real-data and assessed depth", async () => {
    const regenerated = await regenerate();
    const committed = await readFile(
      join(repositoryRoot, "docs", "COMPARISON_AUDIT.md"),
      "utf8",
    );
    expect(providerDepths(committed, "AIDD Commons")).toEqual(
      providerDepths(regenerated.audit, "AIDD Commons"),
    );
    expect(providerDepths(committed, "AIDD Commons")).toHaveLength(
      providerDepthColumns.length,
    );
  });
});
