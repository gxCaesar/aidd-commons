import { describe, expect, it } from "vitest";

import type { ComparisonTaxonomy } from "../../catalog/schema/comparison-taxonomy.js";
import type { ComparisonSystem } from "../../catalog/schema/comparison.js";
import {
  boundsAtThreshold,
  buildComparisonMatrix,
  buildGapTopics,
  buildSelfAuditNeededTopics,
  selectDepthCandidates,
  summarizeBounds,
} from "../../scripts/comparisons/matrix.js";

const taxonomy: ComparisonTaxonomy = {
  version: "0.2a",
  tracks: [
    {
      id: "track-one",
      order: 1,
      topics: [
        {
          id: "topic-one",
          order: 1,
          title: "Topic one",
          description: "The first comparison topic.",
          core: true,
          prerequisites: [],
        },
        {
          id: "topic-two",
          order: 2,
          title: "Topic two",
          description: "The second comparison topic.",
          core: true,
          prerequisites: ["topic-one"],
        },
      ],
    },
  ],
};

function makeSystem(
  id: string,
  coverage: ComparisonSystem["coverage"],
  options: { defaultUnknown?: boolean; repositoryEvidence?: boolean } = {},
): ComparisonSystem {
  const evidence = options.repositoryEvidence
    ? {
        id: "overview",
        repository_path: "docs/ROADMAP_V0.2.md",
        title: "Repository overview",
        observed_scope: "The public repository overview.",
        access: "opened" as const,
        reviewed_on: "2026-09-04",
      }
    : {
        id: "overview",
        url: `https://example.org/${id}`,
        title: "Provider overview",
        observed_scope: "The public provider overview.",
        access: "opened" as const,
        reviewed_on: "2026-09-04",
      };

  return {
    id,
    name: id,
    provider_class: "curriculum",
    canonical_url: `https://example.org/${id}`,
    summary: "A synthetic matrix-test provider.",
    audiences: ["researchers"],
    languages: ["en"],
    metadata_evidence: ["overview"],
    access: {
      content: { value: "unverified" },
      code: { value: "unverified" },
      data: { value: "unverified" },
      solutions: { value: "unverified" },
    },
    licenses: [],
    ...(options.defaultUnknown === false
      ? {}
      : {
          coverage_default: {
            depth: "unverified" as const,
            evidence: [],
            reviewed_scope: "No topic-specific evidence was encoded.",
            note: "Omitted topics remain unverified.",
          },
        }),
    coverage,
    evidence: [evidence],
    caveats: [],
    last_verified: "2026-09-04",
  };
}

describe("comparison matrix", () => {
  it("materializes explicit unknown defaults in provider and taxonomy order", () => {
    const systems = [
      makeSystem("zeta-provider", []),
      makeSystem("alpha-provider", [
        {
          topic_id: "topic-two",
          depth: "explained",
          evidence: ["overview"],
          reviewed_scope: "The public provider overview.",
          note: "The second topic is directly explained.",
        },
      ]),
    ];

    const rows = buildComparisonMatrix(systems, taxonomy);

    expect(
      rows.map(({ provider_id, topic_id }) => `${provider_id}/${topic_id}`),
    ).toEqual([
      "alpha-provider/topic-one",
      "alpha-provider/topic-two",
      "zeta-provider/topic-one",
      "zeta-provider/topic-two",
    ]);
    expect(rows[0]).toMatchObject({
      coverage_origin: "default",
      depth: "unverified",
      evidence: [],
      lower_at_explained: 0,
      upper_at_explained: 1,
    });
    expect(rows[1]).toMatchObject({
      coverage_origin: "direct",
      depth: "explained",
      lower_at_explained: 1,
      upper_at_explained: 1,
    });
  });

  it("does not treat unverified as observed coverage", () => {
    const oneTopicTaxonomy: ComparisonTaxonomy = {
      ...taxonomy,
      tracks: [
        {
          ...taxonomy.tracks[0]!,
          topics: [taxonomy.tracks[0]!.topics[0]!],
        },
      ],
    };
    const matrix = buildComparisonMatrix(
      [makeSystem("provider-a", [])],
      oneTopicTaxonomy,
    );

    expect(
      summarizeBounds(matrix, "explained").get("provider-a"),
    ).toMatchObject({
      lower: 0,
      upper: 1,
      total_topics: 1,
    });
  });

  it("keeps a scoped absent cell outside both bounds", () => {
    const oneTopicTaxonomy: ComparisonTaxonomy = {
      ...taxonomy,
      tracks: [
        {
          ...taxonomy.tracks[0]!,
          topics: [taxonomy.tracks[0]!.topics[0]!],
        },
      ],
    };
    const matrix = buildComparisonMatrix(
      [
        makeSystem("provider-a", [
          {
            topic_id: "topic-one",
            depth: "absent",
            evidence: ["overview"],
            reviewed_scope: "The complete public provider index.",
            note: "The topic was not found on the reviewed surface.",
          },
        ]),
      ],
      oneTopicTaxonomy,
    );

    expect(
      summarizeBounds(matrix, "explained").get("provider-a"),
    ).toMatchObject({
      lower: 0,
      upper: 0,
    });
  });

  it("applies each pedagogical threshold independently", () => {
    const matrix = buildComparisonMatrix(
      [
        makeSystem(
          "provider-a",
          [
            {
              topic_id: "topic-one",
              depth: "explained",
              evidence: ["overview"],
              reviewed_scope: "The public provider overview.",
              note: "The first topic is explained.",
            },
            {
              topic_id: "topic-two",
              depth: "executable",
              evidence: ["overview"],
              reviewed_scope: "The public provider overview.",
              note: "The second topic is executable.",
            },
          ],
          { defaultUnknown: false },
        ),
      ],
      taxonomy,
    );

    expect(summarizeBounds(matrix, "explained").get("provider-a")?.lower).toBe(
      2,
    );
    expect(summarizeBounds(matrix, "worked").get("provider-a")?.lower).toBe(1);
    expect(summarizeBounds(matrix, "executable").get("provider-a")?.lower).toBe(
      1,
    );
    expect(summarizeBounds(matrix, "assessed").get("provider-a")?.lower).toBe(
      0,
    );
  });

  it("lists a gap only with worked-or-deeper external evidence", () => {
    const oneTopicTaxonomy: ComparisonTaxonomy = {
      ...taxonomy,
      tracks: [
        {
          ...taxonomy.tracks[0]!,
          topics: [taxonomy.tracks[0]!.topics[0]!],
        },
      ],
    };
    const matrix = buildComparisonMatrix(
      [
        makeSystem("aidd-commons", [
          {
            topic_id: "topic-one",
            depth: "explained",
            evidence: ["overview"],
            reviewed_scope: "The public provider overview.",
            note: "The topic is explained but not worked.",
          },
        ]),
        makeSystem("worked-provider", [
          {
            topic_id: "topic-one",
            depth: "worked",
            evidence: ["overview"],
            reviewed_scope: "The public provider overview.",
            note: "The topic has a worked example.",
          },
        ]),
        makeSystem("unknown-provider", []),
      ],
      oneTopicTaxonomy,
    );

    expect(buildGapTopics(matrix)).toEqual([
      expect.objectContaining({
        external_providers_at_worked_or_deeper: ["worked-provider"],
        self_depth: "explained",
        strongest_external_depth: "worked",
        topic_id: "topic-one",
      }),
    ]);
  });

  it("keeps an unverified self cell out of confirmed depth gaps", () => {
    const oneTopicTaxonomy: ComparisonTaxonomy = {
      ...taxonomy,
      tracks: [
        {
          ...taxonomy.tracks[0]!,
          topics: [taxonomy.tracks[0]!.topics[0]!],
        },
      ],
    };
    const matrix = buildComparisonMatrix(
      [
        makeSystem("aidd-commons", []),
        makeSystem("worked-provider", [
          {
            topic_id: "topic-one",
            depth: "worked",
            evidence: ["overview"],
            reviewed_scope: "The public provider overview.",
            note: "The topic has a worked example.",
          },
        ]),
      ],
      oneTopicTaxonomy,
    );

    expect(buildGapTopics(matrix)).toEqual([]);
    expect(buildSelfAuditNeededTopics(matrix)).toEqual([
      expect.objectContaining({
        external_providers_at_worked_or_deeper: ["worked-provider"],
        self_depth: "unverified",
        topic_id: "topic-one",
      }),
    ]);
  });

  it("preserves repository evidence as a discriminated source", () => {
    const row = buildComparisonMatrix(
      [
        makeSystem(
          "repository-provider",
          [
            {
              topic_id: "topic-one",
              depth: "worked",
              evidence: ["overview"],
              reviewed_scope: "The public repository overview.",
              note: "The repository contains a worked example.",
            },
          ],
          { repositoryEvidence: true },
        ),
      ],
      taxonomy,
    )[0];

    expect(row?.evidence).toEqual([
      expect.objectContaining({
        source_type: "repository_path",
        repository_path: "docs/ROADMAP_V0.2.md",
      }),
    ]);
    expect(row?.evidence[0]).not.toHaveProperty("url");
  });

  it("rejects an omitted provider-topic cell without an explicit default", () => {
    expect(() =>
      buildComparisonMatrix(
        [makeSystem("incomplete-provider", [], { defaultUnknown: false })],
        taxonomy,
      ),
    ).toThrow("coverage_default");
  });

  it("selects no depth candidate while any eligibility field is unresolved", () => {
    expect(
      selectDepthCandidates([
        {
          topic_id: "topic-one",
          prerequisite_value: 2,
          maintenance: { burden: 1, rationale: "Stable fixture." },
          eligibility: {
            data_feasibility: true,
            cheap_baseline: true,
            independent_unit: true,
            evaluation: true,
            licence: "unverified",
            compute: true,
            safety: true,
          },
        },
      ]),
    ).toEqual([]);
  });

  it("orders fully eligible candidates by prerequisite value then maintenance", () => {
    const allTrue = {
      data_feasibility: true,
      cheap_baseline: true,
      independent_unit: true,
      evaluation: true,
      licence: true,
      compute: true,
      safety: true,
    } as const;

    expect(
      selectDepthCandidates([
        {
          topic_id: "lower-value",
          prerequisite_value: 1,
          maintenance: { burden: 1, rationale: "Stable fixture." },
          eligibility: allTrue,
        },
        {
          topic_id: "higher-maintenance",
          prerequisite_value: 2,
          maintenance: { burden: 3, rationale: "Higher fixture burden." },
          eligibility: allTrue,
        },
        {
          topic_id: "lower-maintenance",
          prerequisite_value: 2,
          maintenance: { burden: 1, rationale: "Lower fixture burden." },
          eligibility: allTrue,
        },
      ]).map(({ topic_id }) => topic_id),
    ).toEqual(["lower-maintenance", "higher-maintenance", "lower-value"]);
  });

  it("counts real-data runnable cells exactly and leaves an unknown basis open", () => {
    const at = "executable-on-real-data" as const;
    expect(boundsAtThreshold("assessed", at, "real-data")).toEqual({
      lower: 1,
      upper: 1,
    });
    expect(boundsAtThreshold("executable", at, "authored")).toEqual({
      lower: 0,
      upper: 0,
    });
    expect(boundsAtThreshold("executable", at, "unverified")).toEqual({
      lower: 0,
      upper: 1,
    });
    expect(boundsAtThreshold("worked", at, null)).toEqual({
      lower: 0,
      upper: 0,
    });
    expect(boundsAtThreshold("unverified", at, null)).toEqual({
      lower: 0,
      upper: 1,
    });
    // The depth thresholds ignore the run basis entirely.
    expect(boundsAtThreshold("executable", "executable", "authored")).toEqual({
      lower: 1,
      upper: 1,
    });
  });
});
