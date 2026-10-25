import type {
  Curriculum,
  CurriculumLesson,
} from "../../../scripts/curriculum/curriculum.js";

export function lessonNavigation(curriculum: Curriculum, lessonId: string) {
  const lessons = new Map<
    string,
    { lesson: CurriculumLesson; track: Curriculum["tracks"][number] }
  >(
    curriculum.tracks.flatMap((track) =>
      track.lessons.map(
        (lesson) => [`${track.id}/${lesson.id}`, { lesson, track }] as const,
      ),
    ),
  );
  const current = lessons.get(lessonId);
  if (!current || current.lesson.type === "core-source-path") return null;

  function link(id: string | undefined) {
    if (!id) return null;
    const entry = lessons.get(id);
    if (!entry || entry.lesson.type === "core-source-path") {
      throw new Error(
        `Learning navigation references an unpublished lesson: ${id}`,
      );
    }
    return {
      id,
      title: entry.lesson.title,
      title_zh: entry.lesson.title_zh ?? entry.lesson.title,
    };
  }

  const routes = curriculum.learning_paths.flatMap((path) => {
    const index = path.lesson_ids.indexOf(lessonId);
    if (index < 0) return [];
    return [
      {
        id: path.id,
        kind: path.kind,
        title: path.title,
        title_zh: path.title_zh,
        position: index + 1,
        total: path.lesson_ids.length,
        previous: link(path.lesson_ids[index - 1]),
        next: link(path.lesson_ids[index + 1]),
      },
    ];
  });

  if (routes.length > 0) return { routes };

  // Chapters outside the six declared routes keep their track's reading order.
  const chapters = current.track.lessons
    .filter((lesson) => lesson.type !== "core-source-path")
    .toSorted((left, right) => left.order - right.order);
  const index = chapters.findIndex((lesson) => lesson.id === current.lesson.id);
  const qualified = (offset: number) => {
    const chapter = chapters[index + offset];
    return chapter ? `${current.track.id}/${chapter.id}` : undefined;
  };
  return {
    routes: [
      {
        id: current.track.id,
        kind: "track" as const,
        title: current.track.title,
        title_zh: current.track.title_zh,
        position: index + 1,
        total: chapters.length,
        previous: link(qualified(-1)),
        next: link(qualified(1)),
      },
    ],
  };
}
