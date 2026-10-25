import { describe, expect, it } from "vitest";
import type { Resource } from "../../catalog/schema/resource.js";
import type { Curriculum } from "../../scripts/curriculum/curriculum.js";
import { buildResourceMap } from "../../scripts/curriculum/resource-map.js";

const resources = [
  {
    id: "data-a",
    name: "Measured data",
    kind: "dataset",
    canonical_url: "https://example.org/data",
    access_level: { value: "unverified" },
  },
  {
    id: "tool-b",
    name: "Analysis tool",
    kind: "software",
    canonical_url: "https://example.org/tool",
    access_level: { value: "open_source" },
  },
] as Resource[];

const curriculum = {
  tracks: [
    {
      id: "example",
      title: "Example",
      title_zh: "示例",
      lessons: [
        {
          id: "lesson-a",
          type: "lesson",
          source_ids: ["data-a", "data-a"],
          capabilities: ["explanation", "exercise"],
        },
        {
          id: "reading",
          type: "core-source-path",
          source_ids: ["tool-b", "data-a"],
        },
      ],
    },
  ],
  units: [
    {
      id: "unit-a",
      track_id: "example",
      title: "First",
      title_zh: "第一",
      lesson_id: "example/lesson-a",
    },
    {
      id: "unit-b",
      track_id: "example",
      title: "Second",
      title_zh: "第二",
      lesson_id: "example/lesson-a",
    },
    { id: "unit-c", track_id: "example", title: "Planned", title_zh: "计划" },
  ],
} as unknown as Curriculum;

describe("current curriculum resource map", () => {
  it("separates inherited lesson reading from pathway reading without turning either into unit coverage", () => {
    const map = buildResourceMap(curriculum, resources);
    expect(map.rows).toHaveLength(3);
    expect(map.rows[0]).toMatchObject({
      unit_id: "unit-a",
      lesson_id: "example/lesson-a",
      lesson_resource_ids: ["data-a"],
      pathway_resource_ids: ["tool-b"],
      capabilities: ["explanation", "exercise"],
      unit_resource_sufficiency: "not_assessed",
    });
    expect(map.rows[1].lesson_resource_ids).toEqual(["data-a"]);
    expect(map.rows[2]).toMatchObject({
      unit_id: "unit-c",
      lesson_id: null,
      lesson_resource_ids: [],
      capabilities: [],
      unit_resource_sufficiency: "not_assessed",
    });
    expect(map.resources.map((resource) => resource.id)).toEqual([
      "data-a",
      "tool-b",
    ]);
  });

  it("rejects a missing referenced resource instead of presenting an incomplete reading list", () => {
    expect(() => buildResourceMap(curriculum, resources.slice(0, 1))).toThrow(
      "tool-b",
    );
  });

  it("rejects a unit mapped to a missing lesson", () => {
    const broken = structuredClone(curriculum);
    broken.units[0].lesson_id = "example/missing";
    expect(() => buildResourceMap(broken, resources)).toThrow(
      "example/missing",
    );
  });
});
