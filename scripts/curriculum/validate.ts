import { loadCatalog } from "../catalog/catalog.js";
import {
  CurriculumValidationError,
  formatCurriculumDiagnostic,
  loadCurriculum,
} from "./curriculum.js";

function parseArguments(argumentsList: string[]): {
  catalog: string;
  input: string;
  today?: string;
} {
  let catalog = "catalog/resources";
  let input = "catalog/curriculum/tracks.yaml";
  let today: string | undefined;

  for (let index = 0; index < argumentsList.length; index += 1) {
    const argument = argumentsList[index];
    if (argument === "--catalog" || argument === "--today") {
      const value = argumentsList[index + 1];
      if (value === undefined) throw new Error(`${argument} requires a value`);
      if (argument === "--catalog") catalog = value;
      else today = value;
      index += 1;
    } else if (argument.startsWith("--")) {
      throw new Error(`Unknown option: ${argument}`);
    } else {
      input = argument;
    }
  }
  return { catalog, input, today };
}

async function main(): Promise<void> {
  const { catalog, input, today } = parseArguments(process.argv.slice(2));
  const resources = await loadCatalog(catalog, { today });
  const curriculum = await loadCurriculum(input, { resources });
  console.log(`Validated ${curriculum.tracks.length} curriculum tracks.`);
}

main().catch((error: unknown) => {
  if (error instanceof CurriculumValidationError) {
    for (const diagnostic of error.diagnostics) {
      console.error(formatCurriculumDiagnostic(diagnostic));
    }
  } else {
    console.error(error instanceof Error ? error.message : String(error));
  }
  process.exitCode = 1;
});
