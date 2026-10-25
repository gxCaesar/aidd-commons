import { describe, expect, it } from "vitest";

import {
  ordinalDepth,
  secondReadingSchema,
  type SecondReading,
} from "../../catalog/schema/second-reading.js";
import { loadComparisonSystems } from "../../scripts/comparisons/comparisons.js";
import { externalSurveyFrozenOn } from "../../scripts/comparisons/export.js";
import {
  checkAgainstSecondReading,
  loadSecondReadings,
} from "../../scripts/comparisons/second-reading.js";
import { loadComparisonTaxonomy } from "../../scripts/comparisons/taxonomy.js";

async function committed() {
  const [systems, taxonomy, readings] = await Promise.all([
    loadComparisonSystems("catalog/comparisons/systems"),
    loadComparisonTaxonomy("catalog/comparisons/taxonomy.yaml"),
    loadSecondReadings("catalog/comparisons/reviews"),
  ]);
  const self = systems.find(({ id }) => id === "aidd-commons");
  if (self === undefined) {
    throw new Error("self record missing");
  }
  return { readings, self, systems, taxonomy };
}

describe("independent second reading", () => {
  it("covers every topic and never sits below the committed self record", async () => {
    const { readings, self, taxonomy } = await committed();
    expect(readings).toHaveLength(1);
    const reading = readings[0]!.reading;
    expect(reading.readings).toHaveLength(93);
    expect(checkAgainstSecondReading(self, reading, taxonomy)).toEqual([]);
  });

  it("compares an assessed reading with nothing runnable as worked", () => {
    const base = {
      evidence_paths: [],
      reason: "An answered exercise and no runnable task.",
      reviewed_commit: "40a6776",
      topic_id: "t01-entity-glossary",
    };
    expect(
      ordinalDepth({ ...base, depth: "assessed", run_basis: "none" }),
    ).toBe("worked");
    expect(
      ordinalDepth({ ...base, depth: "assessed", run_basis: "authored" }),
    ).toBe("assessed");
  });

  it("refuses a self record that claims more than the reading supports", async () => {
    const { readings, self, taxonomy } = await committed();
    const inflated = structuredClone(self);
    const cell = inflated.coverage.find(
      ({ topic_id }) => topic_id === "t06-tractability-target-risk",
    )!;
    cell.depth = "assessed";
    cell.run_basis = "real-data";
    const diagnostics = checkAgainstSecondReading(
      inflated,
      readings[0]!.reading,
      taxonomy,
    );
    expect(diagnostics.map(({ message }) => message)).toEqual([
      "records assessed but the independent reading supports worked",
    ]);
  });

  it("refuses a real-data basis where the reading found authored inputs", async () => {
    const { readings, self, taxonomy } = await committed();
    const relabelled = structuredClone(self);
    const cell = relabelled.coverage.find(
      ({ topic_id }) => topic_id === "t11-docking-scoring-protocol",
    )!;
    expect(cell.run_basis).toBe("authored");
    cell.run_basis = "real-data";
    const diagnostics = checkAgainstSecondReading(
      relabelled,
      readings[0]!.reading,
      taxonomy,
    );
    expect(diagnostics.map(({ field }) => field)).toEqual([
      "t11-docking-scoring-protocol",
    ]);
  });

  it("refuses a reading that leaves a topic unread", async () => {
    const { readings, self, taxonomy } = await committed();
    const partial: SecondReading = structuredClone(readings[0]!.reading);
    partial.readings = partial.readings.filter(
      ({ topic_id }) => topic_id !== "t18-nomination-readiness-next-experiment",
    );
    expect(
      checkAgainstSecondReading(self, partial, taxonomy).map(
        ({ message }) => message,
      ),
    ).toEqual(["has no independent reading"]);
  });

  it("rejects an executable reading that names nothing runnable", async () => {
    const { readings } = await committed();
    const broken = structuredClone(readings[0]!.reading);
    broken.readings[0] = {
      ...broken.readings[0]!,
      depth: "executable",
      run_basis: "none",
    };
    const result = secondReadingSchema.safeParse(broken);
    expect(result.success).toBe(false);
    expect(result.error?.issues.map(({ message }) => message)).toContain(
      "an executable reading needs a runnable task",
    );
  });
});

describe("external survey freeze", () => {
  it("keeps every external record at or before the freeze date", async () => {
    const { systems } = await committed();
    const external = systems.filter(({ id }) => id !== "aidd-commons");
    expect(external).toHaveLength(12);
    for (const system of external) {
      expect(
        system.last_verified <= externalSurveyFrozenOn,
        `${system.id} was re-surveyed on ${system.last_verified}`,
      ).toBe(true);
    }
  });
});
