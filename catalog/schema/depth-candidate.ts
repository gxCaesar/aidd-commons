import { z } from "zod";

import { isCalendarDate, stableIdPattern } from "./resource.js";

const stableId = z
  .string()
  .regex(stableIdPattern, "must use lowercase kebab-case");

function usesHttps(value: string): boolean {
  try {
    return new URL(value).protocol === "https:";
  } catch {
    return false;
  }
}

const httpsUrl = z
  .string()
  .url()
  .refine(usesHttps, "must use the HTTPS scheme");

const calendarDate = z
  .string()
  .refine(isCalendarDate, "must be an ISO calendar date (YYYY-MM-DD)");

const evidenceReferences = z
  .array(stableId)
  .min(1, "must reference at least one evidence entry");

export const depthCandidateEligibilityFields = [
  "data_feasibility",
  "cheap_baseline",
  "independent_unit",
  "evaluation",
  "licence",
  "compute",
  "safety",
] as const;

export type DepthCandidateEligibilityField =
  (typeof depthCandidateEligibilityFields)[number];

const eligibilityValue = z.union([z.boolean(), z.literal("unverified")]);

const depthCandidateEvidenceSchema = z
  .object({
    id: stableId,
    url: httpsUrl,
    title: z.string().trim().min(1),
    observed_scope: z.string().trim().min(1),
    access: z.enum(["opened", "inaccessible"]),
    reviewed_on: calendarDate,
    version: z.string().trim().min(1).optional(),
  })
  .strict();

export const depthCandidateSchema = z
  .object({
    topic_id: stableId,
    track_id: stableId,
    topic_title: z.string().trim().min(1),
    topic_core: z.literal(true),
    self_depth: z.enum(["absent", "mentioned", "explained"]),
    strongest_external_depth: z.enum(["worked", "executable", "assessed"]),
    external_providers_at_worked_or_deeper: z.array(stableId).min(1),
    prerequisite_value: z.number().int().nonnegative(),
    implementation: z
      .object({
        status: z.enum(["planned", "in_progress", "completed"]),
        updated_on: calendarDate,
        note: z.string().trim().min(1),
      })
      .strict(),
    maintenance: z
      .object({
        burden: z.number().int().min(1).max(3),
        rationale: z.string().trim().min(1),
      })
      .strict(),
    eligibility: z
      .object({
        data_feasibility: eligibilityValue,
        cheap_baseline: eligibilityValue,
        independent_unit: eligibilityValue,
        evaluation: eligibilityValue,
        licence: eligibilityValue,
        compute: eligibilityValue,
        safety: eligibilityValue,
      })
      .strict(),
    data_feasibility: z
      .object({
        dataset_name: z.string().trim().min(1),
        dataset_version: z.string().trim().min(1),
        source_url: httpsUrl,
        entity_unit: z.string().trim().min(1),
        inputs: z.array(z.string().trim().min(1)).min(1),
        labels: z.array(z.string().trim().min(1)).min(1),
        observed_entities: z.number().int().positive(),
        evidence: evidenceReferences,
      })
      .strict(),
    cheap_baseline: z
      .object({
        name: z.string().trim().min(1),
        protocol: z.string().trim().min(1),
      })
      .strict(),
    independent_unit: z
      .object({
        name: z.string().trim().min(1),
        observed_units: z.number().int().positive(),
        note: z.string().trim().min(1),
      })
      .strict(),
    evaluation: z
      .object({
        split: z.string().trim().min(1),
        primary_metric: z.string().trim().min(1),
        secondary_metrics: z.array(z.string().trim().min(1)).min(1),
        independent_validation: z.string().trim().min(1),
      })
      .strict(),
    licence: z
      .object({
        name: z.string().trim().min(1),
        scope: z.string().trim().min(1),
        evidence: evidenceReferences,
      })
      .strict(),
    compute: z
      .object({
        device: z.literal("cpu"),
        estimated_download_mb: z.number().nonnegative(),
        estimated_memory_gb: z.number().positive(),
        estimated_runtime_minutes: z.number().positive(),
        basis: z.string().trim().min(1),
      })
      .strict(),
    safety: z
      .object({
        disposition: z.literal("safe_non_operational"),
        rationale: z.string().trim().min(1),
      })
      .strict(),
    evidence: z.array(depthCandidateEvidenceSchema).min(1),
    last_verified: calendarDate,
  })
  .strict()
  .superRefine((candidate, context) => {
    const evidenceById = new Map<string, (typeof candidate.evidence)[number]>();

    for (const [index, evidence] of candidate.evidence.entries()) {
      if (evidenceById.has(evidence.id)) {
        context.addIssue({
          code: z.ZodIssueCode.custom,
          message: "duplicates an evidence id in this candidate",
          path: ["evidence", index, "id"],
        });
      } else {
        evidenceById.set(evidence.id, evidence);
      }
      if (evidence.reviewed_on > candidate.last_verified) {
        context.addIssue({
          code: z.ZodIssueCode.custom,
          message: "cannot be later than the containing candidate review",
          path: ["evidence", index, "reviewed_on"],
        });
      }
    }

    const requireOpenedEvidence = (
      references: string[],
      path: (string | number)[],
    ) => {
      for (const [index, reference] of references.entries()) {
        const evidence = evidenceById.get(reference);
        if (evidence === undefined) {
          context.addIssue({
            code: z.ZodIssueCode.custom,
            message: `does not match an evidence id in this candidate: ${reference}`,
            path: [...path, index],
          });
        } else if (evidence.access !== "opened") {
          context.addIssue({
            code: z.ZodIssueCode.custom,
            message: "must reference opened evidence",
            path: [...path, index],
          });
        }
      }
    };

    requireOpenedEvidence(candidate.data_feasibility.evidence, [
      "data_feasibility",
      "evidence",
    ]);
    requireOpenedEvidence(candidate.licence.evidence, ["licence", "evidence"]);
    if (candidate.implementation.updated_on > candidate.last_verified) {
      context.addIssue({
        code: z.ZodIssueCode.custom,
        message: "cannot be later than the containing candidate review",
        path: ["implementation", "updated_on"],
      });
    }
    if (
      !candidate.data_feasibility.evidence.some(
        (reference) =>
          evidenceById.get(reference)?.url ===
          candidate.data_feasibility.source_url,
      )
    ) {
      context.addIssue({
        code: z.ZodIssueCode.custom,
        message: "must match an opened data-feasibility evidence URL",
        path: ["data_feasibility", "source_url"],
      });
    }
  });

export const depthCandidateSetSchema = z
  .object({
    version: z.literal("0.2b-candidates.v1"),
    selection_rule: z.literal("roadmap-v0.2-2026-09-04"),
    as_of: calendarDate,
    candidates: z.array(depthCandidateSchema).max(3),
  })
  .strict()
  .superRefine((record, context) => {
    const firstIndexByTopic = new Map<string, number>();

    for (const [index, candidate] of record.candidates.entries()) {
      const firstIndex = firstIndexByTopic.get(candidate.topic_id);
      if (firstIndex !== undefined) {
        context.addIssue({
          code: z.ZodIssueCode.custom,
          message: `duplicates topic candidate declared at candidates.${firstIndex}`,
          path: ["candidates", index, "topic_id"],
        });
      } else {
        firstIndexByTopic.set(candidate.topic_id, index);
      }

      if (candidate.last_verified > record.as_of) {
        context.addIssue({
          code: z.ZodIssueCode.custom,
          message: "cannot be later than the candidate-set review date",
          path: ["candidates", index, "last_verified"],
        });
      }
    }
  });

export type DepthCandidate = z.infer<typeof depthCandidateSchema>;
export type DepthCandidateSet = z.infer<typeof depthCandidateSetSchema>;

export type DepthCandidateInput = Pick<
  DepthCandidate,
  "eligibility" | "maintenance" | "prerequisite_value" | "topic_id"
>;

function compareAscii(left: string, right: string): number {
  return left < right ? -1 : left > right ? 1 : 0;
}

export function selectDepthCandidates<T extends DepthCandidateInput>(
  candidates: T[],
  limit = 3,
): T[] {
  return [...candidates]
    .filter((candidate) =>
      depthCandidateEligibilityFields.every(
        (field) => candidate.eligibility[field] === true,
      ),
    )
    .sort(
      (left, right) =>
        right.prerequisite_value - left.prerequisite_value ||
        left.maintenance.burden - right.maintenance.burden ||
        compareAscii(left.topic_id, right.topic_id),
    )
    .slice(0, Math.max(0, limit));
}
