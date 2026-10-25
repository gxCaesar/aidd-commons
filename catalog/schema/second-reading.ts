import { z } from "zod";

import {
  calendarDate,
  depthStates,
  repositoryPath,
  stableId,
  type DepthState,
} from "./comparison.js";

// A second reading of one provider's row by a reviewer who never saw the first.
// It exists because the self-audit of this project is scored by the hand that wrote
// the lessons. The reviewer's 'assessed' needs only an answered exercise, while this
// audit's ordinal rule lets 'assessed' claim 'executable', so a reading of
// 'assessed' with no runnable task is mapped to 'worked' before any comparison.
const readingDepths = depthStates.filter(
  (depth): depth is Exclude<DepthState, "unverified"> => depth !== "unverified",
);

const readingSchema = z
  .object({
    topic_id: stableId,
    depth: z.enum(readingDepths as [string, ...string[]]),
    run_basis: z.enum(["real-data", "authored", "none"]).nullable(),
    reviewed_commit: z.string().regex(/^[0-9a-f]{7,40}$/u),
    evidence_paths: z.array(repositoryPath),
    reason: z.string().trim().min(1),
  })
  .strict()
  .superRefine((reading, context) => {
    const runnableOrAssessed =
      reading.depth === "executable" || reading.depth === "assessed";
    if (runnableOrAssessed && reading.run_basis === null) {
      context.addIssue({
        code: z.ZodIssueCode.custom,
        message: "an executable or assessed reading must state its run basis",
        path: ["run_basis"],
      });
    }
    if (!runnableOrAssessed && reading.run_basis !== null) {
      context.addIssue({
        code: z.ZodIssueCode.custom,
        message: "only an executable or assessed reading has a run basis",
        path: ["run_basis"],
      });
    }
    if (reading.depth === "executable" && reading.run_basis === "none") {
      context.addIssue({
        code: z.ZodIssueCode.custom,
        message: "an executable reading needs a runnable task",
        path: ["run_basis"],
      });
    }
  });

export const secondReadingSchema = z
  .object({
    id: stableId,
    system_id: stableId,
    reviewed_on: calendarDate,
    reviewer: z.string().trim().min(1),
    isolation: z.string().trim().min(1),
    rubric: z.string().trim().min(1),
    ordinal_mapping: z.string().trim().min(1),
    not_evidence_of: z.string().trim().min(1),
    readings: z.array(readingSchema).min(1),
  })
  .strict()
  .superRefine((record, context) => {
    const seen = new Set<string>();
    for (const [index, reading] of record.readings.entries()) {
      if (seen.has(reading.topic_id)) {
        context.addIssue({
          code: z.ZodIssueCode.custom,
          message: "duplicates a topic reading",
          path: ["readings", index, "topic_id"],
        });
      }
      seen.add(reading.topic_id);
    }
  });

export type SecondReading = z.infer<typeof secondReadingSchema>;
export type TopicReading = SecondReading["readings"][number];

// The reading expressed on this audit's ordinal scale.
export function ordinalDepth(
  reading: TopicReading,
): Exclude<DepthState, "unverified"> {
  if (reading.depth === "assessed" && reading.run_basis === "none") {
    return "worked";
  }
  return reading.depth as Exclude<DepthState, "unverified">;
}
