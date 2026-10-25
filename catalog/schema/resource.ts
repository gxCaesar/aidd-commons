import { z } from "zod";

const stableIdPattern = /^[a-z0-9]+(?:-[a-z0-9]+)*$/;

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

const evidenceReferences = z
  .array(stableId)
  .min(1, "must reference at least one evidence entry");

const metadataSupportGroups = [
  "name",
  "kind",
  "summary",
  "identifiers",
  "stages",
  "modalities",
  "tasks",
  "relations",
  "caveats",
  "acknowledgements",
] as const;

const evidenceReferenceSchema = z
  .object({
    id: stableId,
    url: httpsUrl,
    label: z.string().min(1),
    supports: z.array(z.enum(metadataSupportGroups)),
  })
  .strict();

const lifecycleStatuses = [
  "active",
  "legacy",
  "superseded",
  "unmaintained",
  "withdrawn",
  "unverified",
] as const;

const accessLevels = [
  "open_source",
  "open_weights",
  "source_available",
  "research_only",
  "gated",
  "api_only",
  "closed",
  "unverified",
] as const;

const opennessValues = [
  "available",
  "not_available",
  "not_applicable",
  "unverified",
] as const;

const datePattern = /^\d{4}-\d{2}-\d{2}$/;

function isCalendarDate(value: string): boolean {
  if (!datePattern.test(value)) {
    return false;
  }

  const date = new Date(`${value}T00:00:00.000Z`);
  return (
    !Number.isNaN(date.getTime()) && date.toISOString().slice(0, 10) === value
  );
}

const maximumUtcOffsetMilliseconds = 14 * 60 * 60 * 1000;

// Use the latest civil date already in effect anywhere, so a same-day review in
// UTC+8 to UTC+14 is not rejected by a validator running in UTC.
export function latestCurrentCalendarDate(now = new Date()): string {
  return new Date(now.getTime() + maximumUtcOffsetMilliseconds)
    .toISOString()
    .slice(0, 10);
}

function claimSchema<T extends readonly [string, ...string[]]>(values: T) {
  return z
    .object({
      value: z.enum(values),
      evidence: evidenceReferences.optional(),
    })
    .strict()
    .superRefine((claim, context) => {
      if (claim.value !== "unverified" && claim.evidence === undefined) {
        context.addIssue({
          code: z.ZodIssueCode.custom,
          message: "must reference at least one evidence entry",
          path: ["evidence"],
        });
      }
    });
}

const opennessClaimSchema = claimSchema(opennessValues);

export const resourceSchema = z
  .object({
    id: stableId,
    name: z.string().min(1),
    kind: z.string().min(1),
    summary: z.string().min(1),
    canonical_url: httpsUrl,
    identifiers: z.array(
      z
        .object({
          scheme: z.string().min(1),
          value: z.string().min(1),
          url: httpsUrl.optional(),
        })
        .strict(),
    ),
    stages: z.array(z.string().min(1)),
    modalities: z.array(z.string().min(1)),
    tasks: z.array(z.string().min(1)),
    relations: z.array(
      z
        .object({
          type: stableId,
          target: stableId,
        })
        .strict(),
    ),
    status: claimSchema(lifecycleStatuses),
    access_level: claimSchema(accessLevels),
    openness: z
      .object({
        inference_code: opennessClaimSchema,
        training_code: opennessClaimSchema,
        weights: opennessClaimSchema,
        architecture: opennessClaimSchema,
        data_recipe: opennessClaimSchema,
        training_data: opennessClaimSchema,
        evaluation_code: opennessClaimSchema,
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
    evidence: z.array(evidenceReferenceSchema),
    caveats: z.array(z.string().min(1)),
    acknowledgements: z.array(z.string().min(1)),
    last_verified: z
      .string()
      .refine(isCalendarDate, "must be an ISO calendar date (YYYY-MM-DD)"),
  })
  .strict()
  .superRefine((record, context) => {
    const evidenceIds = new Set<string>();
    const metadataValues = {
      name: record.name,
      kind: record.kind,
      summary: record.summary,
      identifiers: record.identifiers,
      stages: record.stages,
      modalities: record.modalities,
      tasks: record.tasks,
      relations: record.relations,
      caveats: record.caveats,
      acknowledgements: record.acknowledgements,
    } satisfies Record<
      (typeof metadataSupportGroups)[number],
      { length: number }
    >;

    for (const [index, evidence] of record.evidence.entries()) {
      if (evidenceIds.has(evidence.id)) {
        context.addIssue({
          code: z.ZodIssueCode.custom,
          message: "duplicates an evidence id in this record",
          path: ["evidence", index, "id"],
        });
      }
      evidenceIds.add(evidence.id);

      for (const [supportIndex, support] of evidence.supports.entries()) {
        if (metadataValues[support].length === 0) {
          context.addIssue({
            code: z.ZodIssueCode.custom,
            message: `cannot support empty metadata group: ${support}`,
            path: ["evidence", index, "supports", supportIndex],
          });
        }
      }
    }

    for (const group of metadataSupportGroups) {
      if (
        metadataValues[group].length > 0 &&
        !record.evidence.some((evidence) => evidence.supports.includes(group))
      ) {
        context.addIssue({
          code: z.ZodIssueCode.custom,
          message: "must be supported by at least one evidence entry",
          path: [group],
        });
      }
    }

    const assertEvidenceReferencesResolve = (
      references: string[] | undefined,
      path: (string | number)[],
    ) => {
      for (const [index, reference] of (references ?? []).entries()) {
        if (!evidenceIds.has(reference)) {
          context.addIssue({
            code: z.ZodIssueCode.custom,
            message: `does not match an evidence id in this record: ${reference}`,
            path: [...path, index],
          });
        }
      }
    };

    assertEvidenceReferencesResolve(record.status.evidence, [
      "status",
      "evidence",
    ]);
    assertEvidenceReferencesResolve(record.access_level.evidence, [
      "access_level",
      "evidence",
    ]);

    for (const [dimension, claim] of Object.entries(record.openness)) {
      assertEvidenceReferencesResolve(claim.evidence, [
        "openness",
        dimension,
        "evidence",
      ]);
    }

    for (const [index, license] of record.licenses.entries()) {
      assertEvidenceReferencesResolve(license.evidence, [
        "licenses",
        index,
        "evidence",
      ]);
    }
  });

export type Resource = z.infer<typeof resourceSchema>;

export { isCalendarDate, stableIdPattern };
