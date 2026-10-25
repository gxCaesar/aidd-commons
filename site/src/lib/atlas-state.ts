export type AtlasQuery = {
  access: string;
  kind: string;
  lifecycle: string;
  q: string;
  stage: string;
};

export type AtlasResource = {
  access_level: { value: string };
  id: string;
  kind: string;
  name: string;
  stages: string[];
  status: { value: string };
  summary: string;
};

export type EvidenceReference = {
  id: string;
  supports: string[];
};

export const progressStorageKey = "aidd-commons:v1:progress";

const queryFields = ["q", "stage", "kind", "access", "lifecycle"] as const;

export function parseAtlasQuery(searchParams: URLSearchParams): AtlasQuery {
  return Object.fromEntries(
    queryFields.map((field) => [field, searchParams.get(field)?.trim() ?? ""]),
  ) as AtlasQuery;
}

export function serializeAtlasQuery(query: AtlasQuery): string {
  const searchParams = new URLSearchParams();

  for (const field of queryFields) {
    if (query[field]) {
      searchParams.set(field, query[field]);
    }
  }

  const serialized = searchParams.toString();
  return serialized ? `?${serialized}` : "";
}

export function filterResources<T extends AtlasResource>(
  resources: T[],
  query: AtlasQuery,
): T[] {
  const searchTerm = query.q.toLocaleLowerCase();

  return resources.filter((resource) => {
    const searchable =
      `${resource.id} ${resource.name} ${resource.summary}`.toLocaleLowerCase();

    return (
      (!searchTerm || searchable.includes(searchTerm)) &&
      (!query.stage || resource.stages.includes(query.stage)) &&
      (!query.kind || resource.kind === query.kind) &&
      (!query.access || resource.access_level.value === query.access) &&
      (!query.lifecycle || resource.status.value === query.lifecycle)
    );
  });
}

export function evidenceForIds<T extends EvidenceReference>(
  evidence: T[],
  ids: string[] | undefined,
): T[] {
  const requestedIds = new Set(ids ?? []);
  return evidence.filter((entry) => requestedIds.has(entry.id));
}

export function evidenceForSupport<T extends EvidenceReference>(
  evidence: T[],
  support: string,
): T[] {
  return evidence.filter((entry) => entry.supports.includes(support));
}

export function toggleLessonProgress(
  completed: string[],
  lessonId: string,
): string[] {
  return completed.includes(lessonId)
    ? completed.filter((id) => id !== lessonId)
    : [...completed, lessonId];
}

export function parseLessonProgress(serialized: string | null): string[] {
  if (!serialized) {
    return [];
  }

  try {
    const parsed = JSON.parse(serialized) as { completed?: unknown };
    if (!Array.isArray(parsed.completed)) {
      return [];
    }

    return [
      ...new Set(
        parsed.completed.filter((id): id is string => typeof id === "string"),
      ),
    ];
  } catch {
    return [];
  }
}

export function readLessonProgress(
  storage: Pick<Storage, "getItem">,
): string[] {
  return parseLessonProgress(storage.getItem(progressStorageKey));
}

export function mergeLessonProgress(
  completed: string[],
  additions: string[],
): string[] {
  return [...new Set([...completed, ...additions])];
}
