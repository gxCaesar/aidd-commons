import { describe, expect, it } from "vitest";

import {
  evidenceForIds,
  evidenceForSupport,
  filterResources,
  mergeLessonProgress,
  parseLessonProgress,
  parseAtlasQuery,
  progressStorageKey,
  readLessonProgress,
  serializeAtlasQuery,
  toggleLessonProgress,
} from "../../site/src/lib/atlas-state.js";

const resources = [
  {
    id: "openfold",
    name: "OpenFold",
    kind: "model",
    summary: "Open structure-prediction implementation.",
    stages: ["structure-prediction"],
    access_level: { value: "open_source" },
    status: { value: "active" },
  },
  {
    id: "freesolv-v0-52",
    name: "FreeSolv v0.52",
    kind: "dataset",
    summary: "Versioned hydration free-energy dataset.",
    stages: ["property-prediction"],
    access_level: { value: "research_only" },
    status: { value: "legacy" },
  },
];

describe("atlas URL state", () => {
  it("parses and serializes shareable atlas filters", () => {
    const query = parseAtlasQuery(
      new URLSearchParams(
        "q=free+solv&stage=property-prediction&kind=dataset&access=research_only&lifecycle=legacy&ignored=value",
      ),
    );

    expect(query).toEqual({
      access: "research_only",
      kind: "dataset",
      lifecycle: "legacy",
      q: "free solv",
      stage: "property-prediction",
    });
    expect(serializeAtlasQuery(query)).toBe(
      "?q=free+solv&stage=property-prediction&kind=dataset&access=research_only&lifecycle=legacy",
    );
  });

  it("maps claim IDs and metadata support to their displayed evidence", () => {
    const evidence = [
      { id: "official-page", supports: ["name", "summary"] },
      { id: "release-doi", supports: ["identifiers", "caveats"] },
    ];

    expect(evidenceForIds(evidence, ["official-page"])).toEqual([
      { id: "official-page", supports: ["name", "summary"] },
    ]);
    expect(evidenceForSupport(evidence, "caveats")).toEqual([
      { id: "release-doi", supports: ["identifiers", "caveats"] },
    ]);
  });

  it("returns only resources that satisfy every active atlas filter", () => {
    const results = filterResources(resources, {
      access: "research_only",
      kind: "dataset",
      lifecycle: "legacy",
      q: "hydration",
      stage: "property-prediction",
    });

    expect(results.map((resource) => resource.id)).toEqual(["freesolv-v0-52"]);
  });
});

describe("lesson progress state", () => {
  it("adds an unfinished lesson and removes it when toggled again", () => {
    const completed = toggleLessonProgress([], "foundations/getting-started");

    expect(completed).toEqual(["foundations/getting-started"]);
    expect(
      toggleLessonProgress(completed, "foundations/getting-started"),
    ).toEqual([]);
  });

  it("keeps only distinct valid lesson identifiers from persisted progress", () => {
    expect(
      parseLessonProgress(
        '{"completed":["foundations/getting-started","foundations/getting-started",3]}',
      ),
    ).toEqual(["foundations/getting-started"]);
    expect(parseLessonProgress("not-json")).toEqual([]);
  });

  it("reads the namespaced progress record and merges distinct completed lessons", () => {
    const stored = readLessonProgress({
      getItem(key) {
        return key === "aidd-commons:v1:progress"
          ? '{"completed":["foundations/getting-started"]}'
          : null;
      },
    });

    expect(progressStorageKey).toBe("aidd-commons:v1:progress");
    expect(
      mergeLessonProgress(stored, [
        "foundations/getting-started",
        "research/reading-papers",
      ]),
    ).toEqual(["foundations/getting-started", "research/reading-papers"]);
  });
});
