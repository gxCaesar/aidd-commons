import { readFile } from "node:fs/promises";
import { parse } from "yaml";
import { describe, expect, it } from "vitest";
import type { Curriculum } from "../../scripts/curriculum/curriculum.js";
import { lessonNavigation } from "../../site/src/lib/lesson-navigation.js";

const curriculum = parse(
  await readFile(
    new URL("../../catalog/curriculum/tracks.yaml", import.meta.url),
    "utf8",
  ),
) as Curriculum;

describe("lesson reading continuity", () => {
  it("starts the declared core route without inventing a previous lesson", () => {
    const first = lessonNavigation(curriculum, "foundations/getting-started")!;
    expect(first.routes).toHaveLength(1);
    expect(first.routes[0]).toMatchObject({
      id: "core",
      position: 1,
      previous: null,
      next: {
        id: "foundations/first-session",
        title:
          "Your first session: representations, evidence, and a completed comparison",
        title_zh: "你的第一次学习",
      },
    });
  });

  it("keeps different successors when a chapter belongs to multiple routes", () => {
    const result = lessonNavigation(
      curriculum,
      "structure-and-pockets/cofolding-frontier",
    )!;
    expect(result.routes.map((route) => route.id)).toEqual([
      "core",
      "structure-physics",
      "biologics",
    ]);
    expect(result.routes.find((route) => route.id === "core")?.next?.id).toBe(
      "physics-based-modeling/docking-to-fep",
    );
    expect(
      result.routes.find((route) => route.id === "structure-physics")?.next?.id,
    ).toBe("structure-and-pockets/structure-affinity-mechanisms");
  });

  it("stops at the end of the core route while retaining specialist continuations", () => {
    const result = lessonNavigation(
      curriculum,
      "candidate-nomination/capstone",
    )!;
    const core = result.routes.find((route) => route.id === "core")!;
    expect(core.position).toBe(core.total);
    expect(core.next).toBeNull();
    expect(
      result.routes.find((route) => route.id === "small-molecules")?.next?.id,
    ).toBe("candidate-nomination/evidence-to-validation");
  });

  it("uses track order for a chapter outside the declared routes and omits source-only entries", () => {
    const reordered = structuredClone(curriculum);
    const track = reordered.tracks.find((item) => item.id === "foundations")!;
    track.lessons.reverse();
    const result = lessonNavigation(
      reordered,
      "foundations/source-review-and-claim-scope",
    )!;
    expect(result.routes).toHaveLength(1);
    expect(result.routes[0]).toMatchObject({
      id: "foundations",
      kind: "track",
      previous: { id: "foundations/evidence-claims-and-unknowns" },
      next: { id: "foundations/entity-kinds-and-identifiers" },
    });
    expect(track.lessons[0]).toEqual(
      curriculum.tracks
        .find((item) => item.id === "foundations")!
        .lessons.at(-1),
    );
  });

  it("leaves non-curriculum and source-only pages to the normal site navigation", () => {
    expect(lessonNavigation(curriculum, "foundations/not-a-lesson")).toBeNull();
    const sourceTrack = curriculum.tracks.find((track) =>
      track.lessons.some((lesson) => lesson.type === "core-source-path"),
    )!;
    const source = sourceTrack.lessons.find(
      (lesson) => lesson.type === "core-source-path",
    )!;
    expect(
      lessonNavigation(curriculum, `${sourceTrack.id}/${source.id}`),
    ).toBeNull();
  });

  it("diagnoses a known unpublished adjacent lesson rather than emitting a dead link", async () => {
    const bad = JSON.parse(
      await readFile(
        new URL(
          "./fixtures/lesson-navigation/bad-unpublished-neighbor.json",
          import.meta.url,
        ),
        "utf8",
      ),
    );
    const changed = structuredClone(curriculum);
    changed.learning_paths.find(
      (route) => route.id === bad.route_id,
    )!.lesson_ids[1] = bad.next_lesson_id;
    expect(() => lessonNavigation(changed, bad.lesson_id)).toThrow(
      `Learning navigation references an unpublished lesson: ${bad.next_lesson_id}`,
    );
  });
});
