import { lstat, readdir, readFile, stat } from "node:fs/promises";
import { extname, relative, resolve } from "node:path";

import { parse } from "yaml";

import {
  comparisonSystemSchema,
  type ComparisonSystem,
} from "../../catalog/schema/comparison.js";
import {
  isCalendarDate,
  latestCurrentCalendarDate,
} from "../../catalog/schema/resource.js";

export type ComparisonDiagnostic = {
  file: string;
  field: string;
  message: string;
};

export class ComparisonValidationError extends Error {
  constructor(readonly diagnostics: ComparisonDiagnostic[]) {
    super(diagnostics.map(formatComparisonDiagnostic).join("\n"));
    this.name = "ComparisonValidationError";
  }
}

export function formatComparisonDiagnostic(
  diagnostic: ComparisonDiagnostic,
): string {
  return `${diagnostic.file}: ${diagnostic.field}: ${diagnostic.message}`;
}

function compareAscii(left: string, right: string): number {
  return left < right ? -1 : left > right ? 1 : 0;
}

async function collectYamlFiles(inputPath: string): Promise<string[]> {
  const input = await stat(inputPath);
  if (input.isFile()) {
    return [inputPath];
  }

  if (!input.isDirectory()) {
    throw new Error(
      `Comparison input is neither a file nor directory: ${inputPath}`,
    );
  }

  const files: string[] = [];
  for (const entry of await readdir(inputPath, { withFileTypes: true })) {
    const child = resolve(inputPath, entry.name);
    if (entry.isDirectory()) {
      files.push(...(await collectYamlFiles(child)));
    } else if (
      entry.isFile() &&
      [".yaml", ".yml"].includes(extname(entry.name).toLowerCase())
    ) {
      files.push(child);
    }
  }
  return files.sort(compareAscii);
}

async function isRegularRepositoryFile(path: string): Promise<boolean> {
  try {
    return (await lstat(resolve(process.cwd(), path))).isFile();
  } catch (error: unknown) {
    if ((error as NodeJS.ErrnoException).code === "ENOENT") {
      return false;
    }
    throw error;
  }
}

export async function loadComparisonSystems(
  inputPath: string,
  options: { today?: string } = {},
): Promise<ComparisonSystem[]> {
  const today = options.today ?? latestCurrentCalendarDate();
  if (!isCalendarDate(today)) {
    throw new Error(`Invalid validator date: ${today}`);
  }

  const diagnostics: ComparisonDiagnostic[] = [];
  const records: Array<{ file: string; system: ComparisonSystem }> = [];
  for (const file of await collectYamlFiles(resolve(inputPath))) {
    const displayFile = relative(process.cwd(), file) || file;
    let source: unknown;
    try {
      source = parse(await readFile(file, "utf8"));
    } catch (error) {
      diagnostics.push({
        file: displayFile,
        field: "$yaml",
        message:
          error instanceof Error ? error.message : "could not parse YAML",
      });
      continue;
    }

    const result = comparisonSystemSchema.safeParse(source);
    if (!result.success) {
      for (const issue of result.error.issues) {
        diagnostics.push({
          file: displayFile,
          field: issue.path.map(String).join(".") || "$record",
          message: issue.message,
        });
      }
      continue;
    }
    if (result.data.last_verified > today) {
      diagnostics.push({
        file: displayFile,
        field: "last_verified",
        message: `cannot be later than validator date ${today}`,
      });
      continue;
    }

    const repositorySources = [
      ...(result.data.canonical_repository_path === undefined
        ? []
        : [
            {
              field: "canonical_repository_path",
              path: result.data.canonical_repository_path,
            },
          ]),
      ...result.data.evidence.flatMap((evidence, index) =>
        evidence.repository_path === undefined
          ? []
          : [
              {
                field: `evidence.${index}.repository_path`,
                path: evidence.repository_path,
              },
            ],
      ),
    ];
    let invalidRepositorySource = false;
    for (const source of repositorySources) {
      if (!(await isRegularRepositoryFile(source.path))) {
        invalidRepositorySource = true;
        diagnostics.push({
          file: displayFile,
          field: source.field,
          message: "does not resolve to a regular repository file",
        });
      }
    }
    if (invalidRepositorySource) {
      continue;
    }
    records.push({ file: displayFile, system: result.data });
  }

  const firstFileById = new Map<string, string>();
  for (const { file, system } of records) {
    const firstFile = firstFileById.get(system.id);
    if (firstFile !== undefined) {
      diagnostics.push({
        file,
        field: "id",
        message: `duplicates comparison system id declared in ${firstFile}`,
      });
    } else {
      firstFileById.set(system.id, file);
    }
  }

  if (diagnostics.length > 0) {
    throw new ComparisonValidationError(diagnostics);
  }

  return records
    .map(({ system }) => system)
    .sort((left, right) => compareAscii(left.id, right.id));
}
