import { basename } from "node:path";

import { loadComparisonSystems } from "./comparisons.js";
import {
  loadDepthCandidateSet,
  validateDepthCandidatesAgainstAudit,
} from "./depth-candidates.js";
import { buildComparisonMatrix, buildGapTopics } from "./matrix.js";
import { assertSecondReadings, loadSecondReadings } from "./second-reading.js";
import { loadComparisonTaxonomy, validateCoverageTopics } from "./taxonomy.js";

type CliOptions = {
  candidates?: string;
  input: string;
  reviews?: string;
  taxonomy: string;
  today?: string;
};

function parseArguments(argumentsList: string[]): CliOptions {
  const defaultInput = "catalog/comparisons/systems";
  const defaultTaxonomy = "catalog/comparisons/taxonomy.yaml";
  let input = defaultInput;
  let candidates: string | undefined;
  let taxonomy = defaultTaxonomy;
  let today: string | undefined;

  for (let index = 0; index < argumentsList.length; index += 1) {
    const argument = argumentsList[index];
    if (argument === "--today") {
      today = argumentsList[index + 1];
      if (today === undefined) {
        throw new Error("--today requires a date");
      }
      index += 1;
    } else if (argument === "--taxonomy") {
      taxonomy = argumentsList[index + 1] ?? "";
      if (taxonomy === "") {
        throw new Error("--taxonomy requires a path");
      }
      index += 1;
    } else if (argument === "--candidates") {
      candidates = argumentsList[index + 1] ?? "";
      if (candidates === "") {
        throw new Error("--candidates requires a path");
      }
      index += 1;
    } else if (argument.startsWith("--")) {
      throw new Error(`Unknown option: ${argument}`);
    } else if (input !== defaultInput) {
      throw new Error(`Unexpected argument: ${argument}`);
    } else {
      input = argument;
    }
  }

  const defaults = input === defaultInput && taxonomy === defaultTaxonomy;
  return {
    candidates:
      candidates ??
      (defaults ? "catalog/comparisons/depth-candidates.yaml" : undefined),
    input,
    reviews: defaults ? "catalog/comparisons/reviews" : undefined,
    taxonomy,
    today,
  };
}

async function main(): Promise<void> {
  const {
    candidates,
    input,
    reviews,
    taxonomy: taxonomyPath,
    today,
  } = parseArguments(process.argv.slice(2));
  const [systems, taxonomy, candidateSet, readings] = await Promise.all([
    loadComparisonSystems(input, { today }),
    loadComparisonTaxonomy(taxonomyPath),
    candidates === undefined
      ? Promise.resolve(undefined)
      : loadDepthCandidateSet(candidates, { today }),
    reviews === undefined ? Promise.resolve([]) : loadSecondReadings(reviews),
  ]);
  validateCoverageTopics(systems, taxonomy);
  assertSecondReadings(systems, readings, taxonomy);
  if (candidateSet !== undefined) {
    const matrix = buildComparisonMatrix(systems, taxonomy);
    const gaps = buildGapTopics(matrix);
    validateDepthCandidatesAgainstAudit(candidateSet, gaps, taxonomy, matrix);
  }
  const noun = systems.length === 1 ? "system" : "systems";
  console.log(`Validated ${systems.length} comparison ${noun}.`);
  if (candidateSet !== undefined) {
    console.log(
      `Validated ${candidateSet.candidates.length} frozen depth candidates.`,
    );
  }
  for (const { reading } of readings) {
    console.log(
      `Validated ${reading.system_id} against the independent reading ${reading.id}.`,
    );
  }
}

const invokedAsCli =
  process.argv[1] !== undefined && basename(process.argv[1]) === "validate.ts";

if (invokedAsCli) {
  main().catch((error: unknown) => {
    console.error(error instanceof Error ? error.message : String(error));
    process.exitCode = 1;
  });
}
