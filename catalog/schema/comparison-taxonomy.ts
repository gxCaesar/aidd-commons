import { z } from "zod";

import { stableIdPattern } from "./resource.js";

const stableId = z
  .string()
  .regex(stableIdPattern, "must use lowercase kebab-case");

const comparisonTopicSchema = z
  .object({
    id: stableId,
    order: z.number().int().positive(),
    title: z.string().trim().min(1),
    description: z.string().trim().min(1),
    core: z.boolean(),
    prerequisites: z.array(stableId),
  })
  .strict();

const comparisonTrackSchema = z
  .object({
    id: stableId,
    order: z.number().int().positive(),
    topics: z.array(comparisonTopicSchema).min(1),
  })
  .strict();

export const comparisonTaxonomySchema = z
  .object({
    version: z.literal("0.2a"),
    tracks: z.array(comparisonTrackSchema).min(1),
  })
  .strict();

export type ComparisonTaxonomy = z.infer<typeof comparisonTaxonomySchema>;
export type ComparisonTrack = ComparisonTaxonomy["tracks"][number];
export type ComparisonTopic = ComparisonTrack["topics"][number];
