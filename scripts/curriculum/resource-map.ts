import type { Resource } from "../../catalog/schema/resource.js";
import { capabilitiesForLesson, type Curriculum } from "./curriculum.js";

export function buildResourceMap(
  curriculum: Curriculum,
  resources: Resource[],
) {
  const byResource = new Map(
    resources.map((resource) => [resource.id, resource]),
  );
  const referencedIds = new Set<string>();
  const unique = (ids: string[]) => [...new Set(ids)];
  const rows = curriculum.units.map((unit) => {
    const track = curriculum.tracks.find((item) => item.id === unit.track_id);
    if (!track) throw new Error(`Unknown unit track: ${unit.track_id}`);
    const lesson = unit.lesson_id
      ? curriculum.tracks
          .flatMap((item) =>
            item.lessons.map((entry) => ({
              entry,
              id: `${item.id}/${entry.id}`,
            })),
          )
          .find((item) => item.id === unit.lesson_id)?.entry
      : undefined;
    if (unit.lesson_id && !lesson)
      throw new Error(`Unknown unit lesson: ${unit.lesson_id}`);
    const lessonIds = unique(lesson?.source_ids ?? []);
    const pathwayIds = unique(
      track.lessons
        .filter((entry) => entry.type === "core-source-path")
        .flatMap((entry) => entry.source_ids),
    ).filter((id) => !lessonIds.includes(id));
    for (const id of [...lessonIds, ...pathwayIds]) {
      if (!byResource.has(id)) throw new Error(`Unknown resource: ${id}`);
      referencedIds.add(id);
    }
    return {
      unit_id: unit.id,
      title: unit.title,
      title_zh: unit.title_zh,
      track_id: track.id,
      lesson_id: unit.lesson_id ?? null,
      capabilities: lesson ? capabilitiesForLesson(lesson) : [],
      lesson_resource_ids: lessonIds,
      pathway_resource_ids: pathwayIds,
      unit_resource_sufficiency: "not_assessed" as const,
    };
  });
  return {
    catalog_resource_count: resources.length,
    reference_scope:
      "Registered lesson and core-path reading; not unit-specific coverage evidence.",
    tracks: curriculum.tracks.map(({ id, title, title_zh }) => ({
      id,
      title,
      title_zh,
    })),
    rows,
    resources: resources
      .filter(({ id }) => referencedIds.has(id))
      .map((resource) => ({
        id: resource.id,
        name: resource.name,
        kind: resource.kind,
        canonical_url: resource.canonical_url,
        access_level: resource.access_level.value,
      })),
  };
}
