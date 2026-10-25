import { mkdir, writeFile } from "node:fs/promises";
import { basename, dirname } from "node:path";

import { format } from "prettier";

import type { Resource } from "../../catalog/schema/resource.js";
import { latestCurrentCalendarDate } from "../../catalog/schema/resource.js";
import { loadCatalog } from "../catalog/catalog.js";
import { loadComparisonSystems } from "../comparisons/comparisons.js";
import { loadDepthCandidateSet } from "../comparisons/depth-candidates.js";
import { buildComparisonExport } from "../comparisons/export.js";
import { loadComparisonTaxonomy } from "../comparisons/taxonomy.js";
import { loadCurriculum } from "./curriculum.js";

export type Coverage = {
  byAccess: Record<string, number>;
  byEvidence: Record<string, number>;
  byKind: Record<string, number>;
  byStage: Record<string, number>;
  byTrack: Record<string, number>;
  comparison: {
    asOf: string;
    directCells: number;
    executableOrAssessedSelfTracks: number;
    externalExplainedUpper: number;
    providerCount: number;
    selectedDepthCandidates: Array<{
      id: string;
      status: string;
      title: string;
    }>;
    selfExplainedLower: number;
    selfWorkedLower: number;
    topicCount: number;
    totalCells: number;
    trackCount: number;
    unknownCells: number;
  };
  resourceCount: number;
};

type BuildCoverageOptions = {
  catalog: string;
  comparisonCandidates?: string;
  comparisonSystems?: string;
  comparisonTaxonomy?: string;
  curriculum: string;
  output: string;
  today?: string;
};

function increment(counts: Record<string, number>, key: string): void {
  counts[key] = (counts[key] ?? 0) + 1;
}

function evidenceState(resource: Resource): string {
  const directClaim =
    resource.status.value !== "unverified" ||
    resource.access_level.value !== "unverified" ||
    resource.licenses.length > 0 ||
    Object.values(resource.openness).some(
      (claim) => claim.value !== "unverified",
    );
  return directClaim ? "claim-backed" : "metadata-supported";
}

function renderTable(counts: Record<string, number>): string {
  const rows = Object.entries(counts).sort(([left], [right]) =>
    left < right ? -1 : left > right ? 1 : 0,
  );
  const categoryWidth = Math.max(
    "Category".length,
    ...rows.map(([category]) => category.length),
  );
  const recordsWidth = Math.max(
    "Records".length,
    ...rows.map(([, count]) => String(count).length),
  );
  const category = (value: string) => value.padEnd(categoryWidth);
  const records = (value: string) => value.padStart(recordsWidth);

  return [
    `| ${category("Category")} | ${records("Records")} |`,
    `| ${"-".repeat(categoryWidth)} | ${"-".repeat(recordsWidth - 1)}: |`,
    ...rows.map(
      ([entry, count]) => `| ${category(entry)} | ${records(String(count))} |`,
    ),
  ].join("\n");
}

export function renderCoverage(coverage: Coverage, today: string): string {
  const selectedCandidateRows = coverage.comparison.selectedDepthCandidates
    .map(
      (candidate, index) =>
        `${index + 1}. \`${candidate.id}\` — ${candidate.title} (${candidate.status});`,
    )
    .join("\n");
  const selfTrackPhrase =
    coverage.comparison.executableOrAssessedSelfTracks === 1
      ? "tracks currently contains"
      : "tracks currently contain";

  return `# AIDD Commons measured coverage

This page is generated from \`catalog/resources/\`,
\`catalog/curriculum/tracks.yaml\`, and \`catalog/comparisons/\` on ${today}. It
reports current measured coverage, not an exhaustive survey of AI drug discovery.

## Overall registry

${coverage.resourceCount} distinct validated resource records are in the current
catalog. A source count is not proof of comprehensiveness: omitted domains,
unverified legal terms, and missing evaluation protocols remain coverage gaps.

## Coverage by curriculum track

Track counts are distinct catalog records referenced by that track's ordered
lesson nodes. One resource may support more than one track, so this table is not
summed into an overall total.

${renderTable(coverage.byTrack)}

## Coverage by resource kind

${renderTable(coverage.byKind)}

## Coverage by pipeline stage

The \`unclassified\` bucket means the record has no stage classification in its
source-backed metadata; it does not mean the resource is unusable.

${renderTable(coverage.byStage)}

## Coverage by access level

${renderTable(coverage.byAccess)}

## Evidence-state interpretation

\`metadata-supported\` means the canonical source supports identity and displayed
metadata while lifecycle, access, licence, and openness remain unverified.
\`claim-backed\` means at least one non-unverified direct claim has adjacent
evidence in that record. Neither state establishes completeness or suitability
for a particular experimental protocol.

${renderTable(coverage.byEvidence)}

## v0.2a measured comparison audit

The comparison audit was regenerated on ${coverage.comparison.asOf} from ${coverage.comparison.providerCount} validated
learning systems, including AIDD Commons. It crosses ${coverage.comparison.topicCount} topic units in all
${coverage.comparison.trackCount} curriculum tracks, producing ${coverage.comparison.totalCells.toLocaleString("en-US")} logical provider-topic cells.
Of these, ${coverage.comparison.directCells} are direct observations and ${coverage.comparison.unknownCells.toLocaleString("en-US")} remain explicit-default
unknowns. Unknown is not treated as absent.

The present evidence does not establish either the "world's most comprehensive"
or the "most detailed" claim. AIDD Commons has an explained-or-deeper lower
bound of ${coverage.comparison.selfExplainedLower} topics, while the strongest external upper bound is
${coverage.comparison.externalExplainedUpper}. Its worked lower bound is ${coverage.comparison.selfWorkedLower}, and only
${coverage.comparison.executableOrAssessedSelfTracks} of the required 12 ${selfTrackPhrase} executable or assessed
self-audit coverage.

${coverage.comparison.selectedDepthCandidates.length} candidates passed every v0.2b eligibility criterion in the frozen selection snapshot:

${selectedCandidateRows || "No candidate passed all frozen criteria."}

These are frozen selection snapshots with live implementation states, not
reported performance experiments. Their records name the data version, entity
and independent unit, split, metric, cheap baseline, independent validation
route, licence evidence, CPU estimate, safety disposition, and maintenance
burden. See [the generated comparison audit](COMPARISON_AUDIT.md) and [the
canonical candidate records](../catalog/comparisons/depth-candidates.yaml).
`;
}

export async function buildCoverage(
  options: BuildCoverageOptions,
): Promise<Coverage> {
  const [resources, comparisonSystems, comparisonTaxonomy, candidateSet] =
    await Promise.all([
      loadCatalog(options.catalog, { today: options.today }),
      loadComparisonSystems(
        options.comparisonSystems ?? "catalog/comparisons/systems",
        { today: options.today },
      ),
      loadComparisonTaxonomy(
        options.comparisonTaxonomy ?? "catalog/comparisons/taxonomy.yaml",
      ),
      loadDepthCandidateSet(
        options.comparisonCandidates ??
          "catalog/comparisons/depth-candidates.yaml",
        { today: options.today },
      ),
    ]);
  const curriculum = await loadCurriculum(options.curriculum, { resources });
  const comparison = buildComparisonExport(
    comparisonSystems,
    comparisonTaxonomy,
    candidateSet,
  );
  const byAccess: Record<string, number> = {};
  const byEvidence: Record<string, number> = {};
  const byKind: Record<string, number> = {};
  const byStage: Record<string, number> = {};
  const byTrack: Record<string, number> = {};

  for (const resource of resources) {
    increment(byAccess, resource.access_level.value);
    increment(byEvidence, evidenceState(resource));
    increment(byKind, resource.kind);
    if (resource.stages.length === 0) increment(byStage, "unclassified");
    else for (const stage of resource.stages) increment(byStage, stage);
  }

  for (const track of curriculum.tracks) {
    const ids = new Set(track.lessons.flatMap((lesson) => lesson.source_ids));
    byTrack[track.id] = ids.size;
  }

  const coverage: Coverage = {
    byAccess,
    byEvidence,
    byKind,
    byStage,
    byTrack,
    comparison: {
      asOf: comparison.as_of,
      directCells: comparison.observations.direct_cells,
      executableOrAssessedSelfTracks:
        comparison.claims.most_detailed.executable_or_assessed_self_tracks,
      externalExplainedUpper:
        comparison.claims.most_comprehensive
          .strongest_external_upper_at_explained,
      providerCount: comparison.providers.length,
      selectedDepthCandidates: comparison.gaps.selected_depth_candidates.map(
        (candidate) => ({
          id: candidate.topic_id,
          status: candidate.implementation.status,
          title: candidate.topic_title,
        }),
      ),
      selfExplainedLower:
        comparison.claims.most_comprehensive.self_lower_at_explained,
      selfWorkedLower: comparison.claims.most_detailed.self_lower_at_worked,
      topicCount: comparison.taxonomy.topics,
      totalCells: comparison.observations.total_cells,
      trackCount: comparison.taxonomy.tracks,
      unknownCells: comparison.observations.default_unverified_cells,
    },
    resourceCount: resources.length,
  };
  const today = options.today ?? latestCurrentCalendarDate();
  await mkdir(dirname(options.output), { recursive: true });
  await writeFile(
    options.output,
    await format(renderCoverage(coverage, today), { parser: "markdown" }),
  );
  return coverage;
}

function parseArguments(argumentsList: string[]): BuildCoverageOptions {
  let catalog = "catalog/resources";
  let curriculum = "catalog/curriculum/tracks.yaml";
  let output = "docs/COVERAGE.md";
  let today: string | undefined;

  for (let index = 0; index < argumentsList.length; index += 1) {
    const argument = argumentsList[index];
    if (
      argument === "--catalog" ||
      argument === "--curriculum" ||
      argument === "--output" ||
      argument === "--today"
    ) {
      const value = argumentsList[index + 1];
      if (value === undefined) throw new Error(`${argument} requires a value`);
      if (argument === "--catalog") catalog = value;
      else if (argument === "--curriculum") curriculum = value;
      else if (argument === "--output") output = value;
      else today = value;
      index += 1;
    } else {
      throw new Error(`Unknown option: ${argument}`);
    }
  }

  return { catalog, curriculum, output, today };
}

async function main(): Promise<void> {
  const options = parseArguments(process.argv.slice(2));
  const coverage = await buildCoverage(options);
  console.log(`Generated coverage for ${coverage.resourceCount} resources.`);
}

const invokedAsCli =
  process.argv[1] !== undefined && basename(process.argv[1]) === "coverage.ts";

if (invokedAsCli) {
  main().catch((error: unknown) => {
    console.error(error instanceof Error ? error.message : String(error));
    process.exitCode = 1;
  });
}
