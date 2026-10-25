import {
  CatalogValidationError,
  formatDiagnostic,
  loadCatalog,
} from "./catalog.js";

function parseArguments(argumentsList: string[]): {
  input: string;
  today?: string;
} {
  let input = "catalog/resources";
  let today: string | undefined;

  for (let index = 0; index < argumentsList.length; index += 1) {
    const argument = argumentsList[index];
    if (argument === "--today") {
      today = argumentsList[index + 1];
      if (today === undefined) {
        throw new Error("--today requires an ISO calendar date");
      }
      index += 1;
    } else if (argument.startsWith("--")) {
      throw new Error(`Unknown option: ${argument}`);
    } else {
      input = argument;
    }
  }

  return { input, today };
}

async function main(): Promise<void> {
  const { input, today } = parseArguments(process.argv.slice(2));
  const resources = await loadCatalog(input, { today });
  console.log(
    `Validated ${resources.length} resource${resources.length === 1 ? "" : "s"}.`,
  );
}

main().catch((error: unknown) => {
  if (error instanceof CatalogValidationError) {
    for (const diagnostic of error.diagnostics) {
      console.error(formatDiagnostic(diagnostic));
    }
  } else {
    console.error(error instanceof Error ? error.message : String(error));
  }
  process.exitCode = 1;
});
