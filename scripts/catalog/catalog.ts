import { readdir, readFile, stat } from "node:fs/promises";
import { extname, relative, resolve } from "node:path";

import { parse } from "yaml";
import {
  resourceSchema,
  type Resource,
  isCalendarDate,
  latestCurrentCalendarDate,
} from "../../catalog/schema/resource.js";

export type CatalogDiagnostic = {
  file: string;
  field: string;
  message: string;
};

export class CatalogValidationError extends Error {
  constructor(readonly diagnostics: CatalogDiagnostic[]) {
    super(diagnostics.map(formatDiagnostic).join("\n"));
    this.name = "CatalogValidationError";
  }
}

export type LoadCatalogOptions = {
  today?: string;
};

export function formatDiagnostic(diagnostic: CatalogDiagnostic): string {
  return `${diagnostic.file}: ${diagnostic.field}: ${diagnostic.message}`;
}

function compareAscii(left: string, right: string): number {
  return left < right ? -1 : left > right ? 1 : 0;
}

export async function loadCatalog(
  inputPath: string,
  options: LoadCatalogOptions = {},
): Promise<Resource[]> {
  const today = options.today ?? latestCurrentCalendarDate();
  if (!isCalendarDate(today)) {
    throw new Error(`Invalid validator date: ${today}`);
  }

  const files = await collectYamlFiles(resolve(inputPath));
  const diagnostics: CatalogDiagnostic[] = [];
  const records: Array<{ file: string; resource: Resource }> = [];

  for (const file of files) {
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

    const result = resourceSchema.safeParse(source);
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

    records.push({ file: displayFile, resource: result.data });
  }

  const ids = new Map<string, string>();
  for (const { file, resource } of records) {
    const firstFile = ids.get(resource.id);
    if (firstFile !== undefined) {
      diagnostics.push({
        file,
        field: "id",
        message: `duplicates resource id declared in ${firstFile}`,
      });
      continue;
    }
    ids.set(resource.id, file);
  }

  for (const { file, resource } of records) {
    for (const [index, relation] of resource.relations.entries()) {
      if (!ids.has(relation.target)) {
        diagnostics.push({
          file,
          field: `relations.${index}.target`,
          message: `does not resolve to a loaded resource id: ${relation.target}`,
        });
      }
    }
  }

  if (diagnostics.length > 0) {
    throw new CatalogValidationError(diagnostics);
  }

  return records
    .map(({ resource }) => resource)
    .sort((left, right) => compareAscii(left.id, right.id));
}

async function collectYamlFiles(inputPath: string): Promise<string[]> {
  const input = await stat(inputPath);
  if (input.isFile()) {
    return [inputPath];
  }

  if (!input.isDirectory()) {
    throw new Error(
      `Catalog input is neither a file nor directory: ${inputPath}`,
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
