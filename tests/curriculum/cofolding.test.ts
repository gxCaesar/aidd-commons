import { describe, expect, it } from "vitest";

import { loadCatalog } from "../../scripts/catalog/catalog.js";

const requiredIds = [
  "model-chai-1",
  "model-chai-2",
  "model-alphafold-3-inference",
  "model-isodde",
  "model-boltz-1",
  "model-boltz-2",
  "model-openfold",
  "model-protenix",
  "model-opendde",
];
const opennessDimensions = [
  "inference_code",
  "training_code",
  "weights",
  "architecture",
  "data_recipe",
  "training_data",
  "evaluation_code",
] as const;

describe("open co-folding frontier records", () => {
  it("contains the required models with all openness dimensions and adjacent direct evidence", async () => {
    expect(requiredIds).toHaveLength(9);
    const resources = await loadCatalog("catalog/resources");
    const byId = new Map(resources.map((resource) => [resource.id, resource]));

    for (const id of requiredIds) {
      const resource = byId.get(id);
      expect(resource, `${id} must be catalogued`).toBeDefined();
      const evidenceIds = new Set(resource?.evidence.map(({ id }) => id));
      expect(Object.keys(resource?.openness ?? {}).sort()).toEqual(
        [...opennessDimensions].sort(),
      );
      for (const dimension of opennessDimensions) {
        const claim = resource!.openness[dimension];
        if (claim.value !== "unverified") {
          expect(claim.evidence?.length).toBeGreaterThan(0);
          expect(claim.evidence?.every((id) => evidenceIds.has(id))).toBe(true);
        }
      }
    }
  });
});
