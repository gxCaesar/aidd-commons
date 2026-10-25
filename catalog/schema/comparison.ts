import { z } from "zod";

import { isCalendarDate, stableIdPattern } from "./resource.js";

export const stableId = z
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

export const calendarDate = z
  .string()
  .refine(isCalendarDate, "must be an ISO calendar date (YYYY-MM-DD)");

const privateRepositorySegments = new Set([
  "experiments",
  "internal",
  "node_modules",
  "playwright-report",
  "private",
  "prompt",
  "prompts",
  "public-release",
  "test-results",
  "tmp",
]);

const privateRepositoryFiles = new Set(["agents.md", "claude.md"]);

export const repositoryPath = z.string().refine((value) => {
  if (value.startsWith("/") || value.includes("\\") || value.includes(":")) {
    return false;
  }
  const segments = value.split("/");
  if (
    !segments.every(
      (segment) =>
        segment !== "" &&
        segment !== "." &&
        segment !== ".." &&
        !segment.startsWith(".") &&
        /^[A-Za-z0-9._-]+$/.test(segment),
    )
  ) {
    return false;
  }

  const normalizedSegments = segments.map((segment) => segment.toLowerCase());
  return (
    !normalizedSegments.some((segment) =>
      privateRepositorySegments.has(segment),
    ) &&
    !privateRepositoryFiles.has(
      normalizedSegments[normalizedSegments.length - 1] ?? "",
    )
  );
}, "must be a repository-relative public path without hidden or internal segments");

const evidenceReferences = z.array(stableId).min(1);

export const depthStates = [
  "absent",
  "mentioned",
  "explained",
  "worked",
  "executable",
  "assessed",
  "unverified",
] as const;

// What a runnable task for a topic rests on. 'real-data' means measured or computed
// records that exist independently of the course carry the lesson, or a genuine
// simulation, docking or structure-prediction run on such inputs; 'authored' means
// hand-written or synthetic illustrative inputs, including real molecules with
// invented values; 'unverified' means the record does not establish which.
export const runBases = ["real-data", "authored", "unverified"] as const;

export const runnableDepths = new Set<string>(["executable", "assessed"]);

const accessValues = [
  "open",
  "gated",
  "paid",
  "institutional",
  "mixed",
  "closed",
  "not_applicable",
  "unverified",
] as const;

const accessClaimSchema = z
  .object({
    value: z.enum(accessValues),
    evidence: evidenceReferences.optional(),
  })
  .strict();

const comparisonEvidenceSchema = z
  .object({
    id: stableId,
    url: httpsUrl.optional(),
    repository_path: repositoryPath.optional(),
    title: z.string().min(1),
    observed_scope: z.string().min(1),
    access: z.enum(["opened", "inaccessible"]),
    reviewed_on: calendarDate,
    version: z.string().min(1).optional(),
  })
  .strict()
  .superRefine((evidence, context) => {
    const sourceCount =
      Number(evidence.url !== undefined) +
      Number(evidence.repository_path !== undefined);
    if (sourceCount !== 1) {
      context.addIssue({
        code: z.ZodIssueCode.custom,
        message: "must define exactly one of url or repository_path",
        path: ["url"],
      });
    }
  });

const coverageObservationSchema = z
  .object({
    topic_id: stableId,
    depth: z.enum(depthStates),
    run_basis: z.enum(runBases).optional(),
    evidence: z.array(stableId),
    reviewed_scope: z.string().trim().min(1),
    note: z.string().min(1),
  })
  .strict()
  .superRefine((observation, context) => {
    const runnable = runnableDepths.has(observation.depth);
    if (runnable && observation.run_basis === undefined) {
      context.addIssue({
        code: z.ZodIssueCode.custom,
        message:
          "must declare run_basis, because a runnable task on authored inputs and one on real data are different deliverables",
        path: ["run_basis"],
      });
    }
    if (!runnable && observation.run_basis !== undefined) {
      context.addIssue({
        code: z.ZodIssueCode.custom,
        message: "run_basis applies only to executable or assessed depth",
        path: ["run_basis"],
      });
    }
  });

const coverageDefaultSchema = z
  .object({
    depth: z.literal("unverified"),
    evidence: z.array(stableId).length(0),
    reviewed_scope: z.string().trim().min(1),
    note: z.string().min(1),
  })
  .strict();

export const comparisonSystemSchema = z
  .object({
    id: stableId,
    name: z.string().min(1),
    provider_class: z.enum([
      "curriculum",
      "tutorial-collection",
      "benchmark-hub",
      "specialist-reference",
    ]),
    canonical_url: httpsUrl.optional(),
    canonical_repository_path: repositoryPath.optional(),
    summary: z.string().min(1),
    audiences: z.array(stableId).min(1),
    languages: z.array(stableId).min(1),
    metadata_evidence: evidenceReferences,
    access: z
      .object({
        content: accessClaimSchema,
        code: accessClaimSchema,
        data: accessClaimSchema,
        solutions: accessClaimSchema,
      })
      .strict(),
    licenses: z.array(
      z
        .object({
          name: z.string().min(1),
          scope: z.string().min(1),
          evidence: evidenceReferences,
        })
        .strict(),
    ),
    correction_url: httpsUrl.optional(),
    correction_evidence: evidenceReferences.optional(),
    coverage_default: coverageDefaultSchema.optional(),
    coverage: z.array(coverageObservationSchema),
    evidence: z.array(comparisonEvidenceSchema).min(1),
    caveats: z.array(z.string().min(1)),
    last_verified: calendarDate,
  })
  .strict()
  .superRefine((record, context) => {
    const canonicalSourceCount =
      Number(record.canonical_url !== undefined) +
      Number(record.canonical_repository_path !== undefined);
    if (canonicalSourceCount !== 1) {
      context.addIssue({
        code: z.ZodIssueCode.custom,
        message:
          "must define exactly one of canonical_url or canonical_repository_path",
        path: ["canonical_url"],
      });
    }

    const evidenceById = new Map<string, (typeof record.evidence)[number]>();
    for (const [index, evidence] of record.evidence.entries()) {
      if (evidenceById.has(evidence.id)) {
        context.addIssue({
          code: z.ZodIssueCode.custom,
          message: "duplicates an evidence id in this record",
          path: ["evidence", index, "id"],
        });
      } else {
        evidenceById.set(evidence.id, evidence);
      }

      if (evidence.reviewed_on > record.last_verified) {
        context.addIssue({
          code: z.ZodIssueCode.custom,
          message: "cannot be later than the containing record review",
          path: ["evidence", index, "reviewed_on"],
        });
      }
    }

    const resolveEvidence = (
      references: string[],
      path: (string | number)[],
      requireOpened: boolean,
    ) => {
      for (const [index, reference] of references.entries()) {
        const evidence = evidenceById.get(reference);
        if (evidence === undefined) {
          context.addIssue({
            code: z.ZodIssueCode.custom,
            message: `does not match an evidence id in this record: ${reference}`,
            path: [...path, index],
          });
        } else if (requireOpened && evidence.access !== "opened") {
          context.addIssue({
            code: z.ZodIssueCode.custom,
            message: "must reference opened evidence",
            path: [...path, index],
          });
        }
      }
    };

    resolveEvidence(record.metadata_evidence, ["metadata_evidence"], true);

    for (const [dimension, claim] of Object.entries(record.access)) {
      const requiresOpenedEvidence = claim.value !== "unverified";
      if (requiresOpenedEvidence && claim.evidence === undefined) {
        context.addIssue({
          code: z.ZodIssueCode.custom,
          message: "must reference at least one evidence entry",
          path: ["access", dimension, "evidence"],
        });
      }
      resolveEvidence(
        claim.evidence ?? [],
        ["access", dimension, "evidence"],
        requiresOpenedEvidence,
      );
    }

    for (const [index, license] of record.licenses.entries()) {
      resolveEvidence(license.evidence, ["licenses", index, "evidence"], true);
    }

    if (
      record.correction_url !== undefined &&
      record.correction_evidence === undefined
    ) {
      context.addIssue({
        code: z.ZodIssueCode.custom,
        message: "must reference evidence for the correction route",
        path: ["correction_evidence"],
      });
    }
    resolveEvidence(
      record.correction_evidence ?? [],
      ["correction_evidence"],
      true,
    );

    const observedTopics = new Set<string>();
    for (const [index, observation] of record.coverage.entries()) {
      if (observedTopics.has(observation.topic_id)) {
        context.addIssue({
          code: z.ZodIssueCode.custom,
          message: "duplicates a topic observation in this record",
          path: ["coverage", index, "topic_id"],
        });
      } else {
        observedTopics.add(observation.topic_id);
      }

      const requiresOpenedEvidence = observation.depth !== "unverified";
      if (requiresOpenedEvidence && observation.evidence.length === 0) {
        context.addIssue({
          code: z.ZodIssueCode.custom,
          message: "must reference at least one evidence entry",
          path: ["coverage", index, "evidence"],
        });
      }
      resolveEvidence(
        observation.evidence,
        ["coverage", index, "evidence"],
        requiresOpenedEvidence,
      );
    }
  });

export type ComparisonSystem = z.infer<typeof comparisonSystemSchema>;
export type DepthState = (typeof depthStates)[number];
export type RunBasis = (typeof runBases)[number];
