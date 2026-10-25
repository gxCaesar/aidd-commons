import { readFile } from "node:fs/promises";
import { relative, resolve } from "node:path";
import { fileURLToPath } from "node:url";

import { parse } from "yaml";
import { z } from "zod";

import type { Resource } from "../../catalog/schema/resource.js";

const stableIdPattern = /^[a-z0-9]+(?:-[a-z0-9]+)*$/;
const stableId = z
  .string()
  .regex(stableIdPattern, "must use lowercase kebab-case");

const lessonTypes = ["intro", "lesson", "core-source-path"] as const;
export const lessonCapabilities = [
  "orientation",
  "explanation",
  "worked-example",
  "exercise",
  "runnable",
] as const;
const qualifiedLessonId = z
  .string()
  .regex(
    new RegExp(
      `^${stableIdPattern.source.slice(1, -1)}/${stableIdPattern.source.slice(1, -1)}$`,
    ),
    "must use a qualified track/lesson ID",
  );
const requiredIntroSections = [
  "foundations",
  "practical-workflow",
  "evaluation",
  "frontier-open-questions",
  "v0-1-omissions",
] as const;

const lessonSchema = z
  .object({
    id: stableId,
    order: z.number().int().positive(),
    title: z.string().min(1),
    title_zh: z.string().min(1).optional(),
    type: z.enum(lessonTypes),
    sections: z.array(z.string().min(1)),
    source_ids: z.array(stableId).min(1),
    prerequisites: z.array(stableId),
    capabilities: z.array(z.enum(lessonCapabilities)).optional(),
  })
  .strict();

const learningPathSchema = z
  .object({
    id: stableId,
    kind: z.enum(["core", "specialist"]),
    title: z.string().min(1),
    title_zh: z.string().min(1),
    description: z.string().min(1),
    description_zh: z.string().min(1),
    lesson_ids: z.array(qualifiedLessonId).min(1),
    prerequisites: z.array(qualifiedLessonId).optional().default([]),
  })
  .strict();

const curriculumUnitSchema = z
  .object({
    id: stableId,
    track_id: stableId,
    title: z.string().min(1),
    title_zh: z.string().min(1),
    learning_objective: z.string().min(1),
    learning_objective_zh: z.string().min(1),
    layer: z.enum(["core", "research", "practice"]),
    prerequisites: z.array(stableId),
    historical_topic_ids: z.array(stableId).min(1),
    lesson_id: qualifiedLessonId.optional(),
  })
  .strict();

const trackSchema = z
  .object({
    id: stableId,
    order: z.number().int().positive(),
    title: z.string().min(1),
    title_zh: z.string().min(1),
    summary: z.string().min(1),
    summary_zh: z.string().min(1),
    audience: z.array(z.string().min(1)).min(1),
    learning_outcomes: z.array(z.string().min(1)).min(2),
    prerequisites: z.array(z.string().min(1)),
    cross_track_prerequisites: z.array(stableId),
    pipeline_stages: z.array(z.string().min(1)).min(1),
    coverage_state: z.enum(["curated-intro-core-source"]),
    lessons: z.array(lessonSchema).min(2),
  })
  .strict();

const curriculumSchema = z
  .object({
    version: z.literal("0.1"),
    tracks: z.array(trackSchema).min(1),
    learning_paths: z.array(learningPathSchema).optional().default([]),
    units: z.array(curriculumUnitSchema).optional().default([]),
  })
  .strict();

export type Curriculum = z.infer<typeof curriculumSchema>;
export type LessonCapability = (typeof lessonCapabilities)[number];
export type CurriculumLesson = Curriculum["tracks"][number]["lessons"][number];

export function capabilitiesForLesson(
  lesson: Pick<CurriculumLesson, "capabilities" | "type">,
): LessonCapability[] {
  if (lesson.capabilities !== undefined) return lesson.capabilities;
  return lesson.type === "intro" ? ["orientation"] : [];
}

export type CurriculumDiagnostic = {
  file: string;
  field: string;
  message: string;
};

export class CurriculumValidationError extends Error {
  constructor(readonly diagnostics: CurriculumDiagnostic[]) {
    super(diagnostics.map(formatCurriculumDiagnostic).join("\n"));
    this.name = "CurriculumValidationError";
  }
}

export const expectedTrackIds = [
  "foundations",
  "drug-discovery-foundations",
  "machine-learning",
  "data-governance",
  "representations",
  "mechanism-targets",
  "qsar-properties",
  "admet-pk",
  "dti-screening",
  "structure-and-pockets",
  "physics-based-modeling",
  "molecular-generation",
  "biologics-design",
  "synthesis-and-automation",
  "active-learning",
  "scientific-agents",
  "evaluation-and-reproducibility",
  "candidate-nomination",
] as const;

export function formatCurriculumDiagnostic(
  diagnostic: CurriculumDiagnostic,
): string {
  return `${diagnostic.file}: ${diagnostic.field}: ${diagnostic.message}`;
}

async function loadHistoricalTopicTracks(): Promise<Map<string, string>> {
  const taxonomyPath = fileURLToPath(
    new URL("../../catalog/comparisons/taxonomy.yaml", import.meta.url),
  );
  const taxonomy = parse(await readFile(taxonomyPath, "utf8")) as {
    tracks?: Array<{
      id?: unknown;
      topics?: Array<{ id?: unknown }>;
    }>;
  };
  const historicalTopicTracks = new Map<string, string>();

  if (!Array.isArray(taxonomy.tracks)) {
    throw new Error("immutable comparison taxonomy has no tracks array");
  }
  for (const track of taxonomy.tracks) {
    if (typeof track.id !== "string" || !Array.isArray(track.topics)) {
      throw new Error("immutable comparison taxonomy has an invalid track");
    }
    for (const topic of track.topics) {
      if (typeof topic.id !== "string") {
        throw new Error("immutable comparison taxonomy has an invalid topic");
      }
      historicalTopicTracks.set(topic.id, track.id);
    }
  }
  return historicalTopicTracks;
}

export async function loadCurriculum(
  inputPath: string,
  options: { resources: Resource[] },
): Promise<Curriculum> {
  const input = resolve(inputPath);
  const file = relative(process.cwd(), input) || input;
  let source: unknown;

  try {
    source = parse(await readFile(input, "utf8"), { merge: true });
  } catch (error) {
    throw new CurriculumValidationError([
      {
        file,
        field: "$yaml",
        message:
          error instanceof Error ? error.message : "could not parse YAML",
      },
    ]);
  }

  const result = curriculumSchema.safeParse(source);
  if (!result.success) {
    throw new CurriculumValidationError(
      result.error.issues.map((issue) => ({
        file,
        field: issue.path.map(String).join(".") || "$curriculum",
        message: issue.message,
      })),
    );
  }

  const curriculum = result.data;
  const diagnostics: CurriculumDiagnostic[] = [];
  const trackIds = new Map<string, number>();
  const lessonIds = new Map<
    string,
    { trackIndex: number; lessonIndex: number }
  >();
  const qualifiedLessons = new Map<
    string,
    {
      lesson: CurriculumLesson;
      lessonIndex: number;
      trackId: string;
      trackIndex: number;
    }
  >();
  const resourceIds = new Set(options.resources.map((resource) => resource.id));

  if (curriculum.tracks.length !== expectedTrackIds.length) {
    diagnostics.push({
      file,
      field: "tracks",
      message: `must define exactly ${expectedTrackIds.length} tracks`,
    });
  }

  for (const [trackIndex, track] of curriculum.tracks.entries()) {
    const expectedId = expectedTrackIds[trackIndex];
    if (track.id !== expectedId) {
      diagnostics.push({
        file,
        field: `tracks.${trackIndex}.id`,
        message: `must be ${expectedId ?? "an expected charter track ID"}`,
      });
    }
    if (trackIds.has(track.id)) {
      diagnostics.push({
        file,
        field: `tracks.${trackIndex}.id`,
        message: `duplicates track ID declared at tracks.${trackIds.get(track.id)}`,
      });
    }
    trackIds.set(track.id, trackIndex);

    for (const [lessonIndex, lesson] of track.lessons.entries()) {
      if (lesson.order !== lessonIndex + 1) {
        diagnostics.push({
          file,
          field: `tracks.${trackIndex}.lessons.${lessonIndex}.order`,
          message: "must be sequential within its track starting at 1",
        });
      }
      if (lessonIds.has(lesson.id)) {
        const first = lessonIds.get(lesson.id)!;
        diagnostics.push({
          file,
          field: `tracks.${trackIndex}.lessons.${lessonIndex}.id`,
          message: `duplicates lesson ID declared at tracks.${first.trackIndex}.lessons.${first.lessonIndex}`,
        });
      }
      lessonIds.set(lesson.id, { trackIndex, lessonIndex });
      qualifiedLessons.set(`${track.id}/${lesson.id}`, {
        lesson,
        lessonIndex,
        trackId: track.id,
        trackIndex,
      });

      for (const [sourceIndex, sourceId] of lesson.source_ids.entries()) {
        if (!resourceIds.has(sourceId)) {
          diagnostics.push({
            file,
            field: `tracks.${trackIndex}.lessons.${lessonIndex}.source_ids.${sourceIndex}`,
            message: `does not resolve to a loaded resource ID: ${sourceId}`,
          });
        }
      }
    }

    const intro = track.lessons.find((lesson) => lesson.type === "intro");
    if (intro === undefined) {
      diagnostics.push({
        file,
        field: `tracks.${trackIndex}.lessons`,
        message: "must contain an intro lesson",
      });
    } else {
      for (const section of requiredIntroSections) {
        if (!intro.sections.includes(section)) {
          diagnostics.push({
            file,
            field: `tracks.${trackIndex}.lessons.${track.lessons.indexOf(intro)}.sections`,
            message: `intro must include ${section}`,
          });
        }
      }
    }
    if (!track.lessons.some((lesson) => lesson.type === "core-source-path")) {
      diagnostics.push({
        file,
        field: `tracks.${trackIndex}.lessons`,
        message: "must contain a core-source-path lesson",
      });
    }
  }

  for (const [trackIndex, track] of curriculum.tracks.entries()) {
    for (const [
      prerequisiteIndex,
      prerequisite,
    ] of track.cross_track_prerequisites.entries()) {
      if (!trackIds.has(prerequisite)) {
        diagnostics.push({
          file,
          field: `tracks.${trackIndex}.cross_track_prerequisites.${prerequisiteIndex}`,
          message: `does not resolve to a curriculum track ID: ${prerequisite}`,
        });
      }
    }

    for (const [lessonIndex, lesson] of track.lessons.entries()) {
      for (const [
        prerequisiteIndex,
        prerequisite,
      ] of lesson.prerequisites.entries()) {
        const referencedLesson = lessonIds.get(prerequisite);
        if (referencedLesson === undefined) {
          diagnostics.push({
            file,
            field: `tracks.${trackIndex}.lessons.${lessonIndex}.prerequisites.${prerequisiteIndex}`,
            message: `does not resolve to a curriculum lesson ID: ${prerequisite}`,
          });
          continue;
        }
        const isEarlierInItsTrack =
          referencedLesson.trackIndex !== trackIndex ||
          referencedLesson.lessonIndex < lessonIndex;
        if (!isEarlierInItsTrack) {
          diagnostics.push({
            file,
            field: `tracks.${trackIndex}.lessons.${lessonIndex}.prerequisites.${prerequisiteIndex}`,
            message:
              "must point to an earlier lesson when it is in the same track",
          });
        }
      }
    }
  }

  const graph = new Map(
    curriculum.tracks.map((track) => [
      track.id,
      track.cross_track_prerequisites,
    ]),
  );
  const visiting = new Set<string>();
  const visited = new Set<string>();
  const visit = (trackId: string): void => {
    if (visited.has(trackId) || !graph.has(trackId)) return;
    if (visiting.has(trackId)) {
      diagnostics.push({
        file,
        field: "cross_track_prerequisites",
        message: `contains a cycle at ${trackId}`,
      });
      return;
    }
    visiting.add(trackId);
    for (const prerequisite of graph.get(trackId) ?? []) visit(prerequisite);
    visiting.delete(trackId);
    visited.add(trackId);
  };
  for (const trackId of graph.keys()) visit(trackId);

  const learningPathIds = new Map<string, number>();
  for (const [pathIndex, path] of curriculum.learning_paths.entries()) {
    if (learningPathIds.has(path.id)) {
      diagnostics.push({
        file,
        field: `learning_paths.${pathIndex}.id`,
        message: `duplicates learning path ID declared at learning_paths.${learningPathIds.get(path.id)}`,
      });
    }
    learningPathIds.set(path.id, pathIndex);

    const lessonPositions = new Map<string, number>();
    for (const [lessonIndex, lessonId] of path.lesson_ids.entries()) {
      if (lessonPositions.has(lessonId)) {
        diagnostics.push({
          file,
          field: `learning_paths.${pathIndex}.lesson_ids.${lessonIndex}`,
          message: `duplicates lesson ID declared at learning_paths.${pathIndex}.lesson_ids.${lessonPositions.get(lessonId)}`,
        });
      }
      lessonPositions.set(lessonId, lessonIndex);

      const lesson = qualifiedLessons.get(lessonId);
      if (lesson === undefined) {
        diagnostics.push({
          file,
          field: `learning_paths.${pathIndex}.lesson_ids.${lessonIndex}`,
          message: "does not resolve to a canonical delivered lesson ID",
        });
      } else if (lesson.lesson.type === "core-source-path") {
        diagnostics.push({
          file,
          field: `learning_paths.${pathIndex}.lesson_ids.${lessonIndex}`,
          message:
            "core-source-path entries are readings, not delivered lessons",
        });
      }
    }

    for (const [
      prerequisiteIndex,
      prerequisite,
    ] of path.prerequisites.entries()) {
      const lesson = qualifiedLessons.get(prerequisite);
      if (lesson === undefined) {
        diagnostics.push({
          file,
          field: `learning_paths.${pathIndex}.prerequisites.${prerequisiteIndex}`,
          message: "does not resolve to a canonical delivered lesson ID",
        });
      } else if (lesson.lesson.type === "core-source-path") {
        diagnostics.push({
          file,
          field: `learning_paths.${pathIndex}.prerequisites.${prerequisiteIndex}`,
          message:
            "core-source-path entries are readings, not delivered lessons",
        });
      }
    }

    if (path.kind !== "core") continue;
    for (const [lessonIndex, lessonId] of path.lesson_ids.entries()) {
      const lesson = qualifiedLessons.get(lessonId);
      if (lesson === undefined) continue;
      for (const prerequisite of lesson.lesson.prerequisites) {
        const prerequisiteLocation = lessonIds.get(prerequisite);
        if (prerequisiteLocation === undefined) continue;
        const prerequisiteTrack =
          curriculum.tracks[prerequisiteLocation.trackIndex];
        const prerequisiteLesson =
          prerequisiteTrack?.lessons[prerequisiteLocation.lessonIndex];
        if (prerequisiteTrack === undefined || prerequisiteLesson === undefined)
          continue;
        const prerequisiteId = `${prerequisiteTrack.id}/${prerequisiteLesson.id}`;
        const prerequisitePosition = lessonPositions.get(prerequisiteId);
        if (prerequisitePosition === undefined) {
          if (!path.prerequisites.includes(prerequisiteId)) {
            diagnostics.push({
              file,
              field: `learning_paths.${pathIndex}.lesson_ids.${lessonIndex}`,
              message: `core route must include ${prerequisiteId} before ${lessonId} or declare it outside the route`,
            });
          }
        } else if (prerequisitePosition >= lessonIndex) {
          diagnostics.push({
            file,
            field: `learning_paths.${pathIndex}.lesson_ids.${lessonIndex}`,
            message: `core route must place ${prerequisiteId} before ${lessonId}`,
          });
        }
      }
    }
  }

  const unitIds = new Map<string, number>();
  let historicalTopicTracks = new Map<string, string>();
  if (curriculum.units.length > 0) {
    try {
      historicalTopicTracks = await loadHistoricalTopicTracks();
    } catch (error) {
      diagnostics.push({
        file,
        field: "units",
        message:
          error instanceof Error
            ? `could not load immutable comparison taxonomy: ${error.message}`
            : "could not load immutable comparison taxonomy",
      });
    }
  }

  for (const [unitIndex, unit] of curriculum.units.entries()) {
    if (unitIds.has(unit.id)) {
      diagnostics.push({
        file,
        field: `units.${unitIndex}.id`,
        message: `duplicates unit ID declared at units.${unitIds.get(unit.id)}`,
      });
    }
    unitIds.set(unit.id, unitIndex);

    if (!trackIds.has(unit.track_id)) {
      diagnostics.push({
        file,
        field: `units.${unitIndex}.track_id`,
        message: "does not resolve to a curriculum track ID",
      });
    }
    for (const [topicIndex, topicId] of unit.historical_topic_ids.entries()) {
      const historicalTrackId = historicalTopicTracks.get(topicId);
      if (historicalTrackId === undefined) {
        diagnostics.push({
          file,
          field: `units.${unitIndex}.historical_topic_ids.${topicIndex}`,
          message: "does not resolve to a historical taxonomy topic ID",
        });
      } else if (historicalTrackId !== unit.track_id) {
        diagnostics.push({
          file,
          field: `units.${unitIndex}.historical_topic_ids.${topicIndex}`,
          message: `belongs to historical track ${historicalTrackId}, not ${unit.track_id}`,
        });
      }
    }
    if (unit.lesson_id !== undefined) {
      const lesson = qualifiedLessons.get(unit.lesson_id);
      if (lesson === undefined) {
        diagnostics.push({
          file,
          field: `units.${unitIndex}.lesson_id`,
          message: "does not resolve to a canonical delivered lesson ID",
        });
      } else if (lesson.lesson.type === "core-source-path") {
        diagnostics.push({
          file,
          field: `units.${unitIndex}.lesson_id`,
          message:
            "core-source-path entries are readings, not delivered lessons",
        });
      } else if (lesson.trackId !== unit.track_id) {
        diagnostics.push({
          file,
          field: `units.${unitIndex}.lesson_id`,
          message: `must belong to unit track ${unit.track_id}`,
        });
      }
    }
  }

  const unitGraph = new Map(
    curriculum.units.map((unit) => [unit.id, unit.prerequisites]),
  );
  const visitingUnits = new Set<string>();
  const visitedUnits = new Set<string>();
  const visitUnit = (unitId: string): void => {
    if (visitedUnits.has(unitId) || !unitGraph.has(unitId)) return;
    if (visitingUnits.has(unitId)) {
      diagnostics.push({
        file,
        field: "units",
        message: `unit prerequisites contains a cycle at ${unitId}`,
      });
      return;
    }
    visitingUnits.add(unitId);
    const unitIndex = unitIds.get(unitId);
    for (const [prerequisiteIndex, prerequisite] of (
      unitGraph.get(unitId) ?? []
    ).entries()) {
      if (!unitIds.has(prerequisite)) {
        diagnostics.push({
          file,
          field: `units.${unitIndex}.prerequisites.${prerequisiteIndex}`,
          message: "does not resolve to a curriculum unit ID",
        });
        continue;
      }
      visitUnit(prerequisite);
    }
    visitingUnits.delete(unitId);
    visitedUnits.add(unitId);
  };
  for (const unitId of unitGraph.keys()) visitUnit(unitId);

  if (diagnostics.length > 0) {
    throw new CurriculumValidationError(diagnostics);
  }
  return curriculum;
}
