import type { AtlasResource } from "../lib/atlas-state.js";

export const opennessDimensions = [
  "inference_code",
  "training_code",
  "weights",
  "architecture",
  "data_recipe",
  "training_data",
  "evaluation_code",
] as const;

export type OpennessDimension = (typeof opennessDimensions)[number];

export type ResourceClaim = {
  evidence?: string[];
  value: string;
};

export type Resource = Omit<AtlasResource, "access_level" | "status"> & {
  acknowledgements: string[];
  access_level: ResourceClaim;
  canonical_url: string;
  caveats: string[];
  evidence: Array<{
    id: string;
    label: string;
    supports: string[];
    url: string;
  }>;
  identifiers: Array<{
    scheme: string;
    url?: string;
    value: string;
  }>;
  last_verified: string;
  licenses: Array<{
    evidence: string[];
    name: string;
    scope: string;
  }>;
  openness: Record<OpennessDimension, ResourceClaim>;
  relations: Array<{ target: string; type: string }>;
  status: ResourceClaim;
  tasks: string[];
  modalities: string[];
};
