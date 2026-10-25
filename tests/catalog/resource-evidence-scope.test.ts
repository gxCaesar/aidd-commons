import { describe, expect, it } from "vitest";
import { loadCatalog } from "../../scripts/catalog/catalog.js";

// These reviewed records establish retrieval, not a defined training release.
// Reintroducing a download-derived training claim must fail.
const retrievalRecords = [
  "db-open-targets-platform",
  "db-gwas-catalog",
  "dataset-cellxgene-census",
  "dataset-jump-cell-painting",
  "db-human-protein-atlas",
  "dataset-prism-repurposing",
  "db-pk-db",
  "db-oas",
  "db-thera-sabdab",
  "db-iedb",
  "dataset-toxcast",
];

describe("reviewed resource evidence scope", () => {
  it("does not promote generic database retrieval to model-training-data availability", async () => {
    const resources = await loadCatalog("catalog/resources");
    for (const id of retrievalRecords) {
      const resource = resources.find((entry) => entry.id === id);
      expect(resource, id).toBeDefined();
      expect(resource!.openness.training_data, id).toEqual({
        value: "unverified",
      });
    }
  });

  it("retains the PK-Sim licence addendum and points to the actual licence file", async () => {
    const [resource] = await loadCatalog("catalog/resources/tool-pk-sim.yaml");
    expect(resource.licenses[0].name).toBe("GPL-2.0 with clarifying addendum");
    const licenceSources = resource.licenses[0].evidence.map(
      (id) => resource.evidence.find((entry) => entry.id === id)?.url,
    );
    expect(licenceSources).toContain(
      "https://raw.githubusercontent.com/Open-Systems-Pharmacology/PK-Sim/develop/LICENSE",
    );
  });

  it.each([
    [
      "tool-openadmet-models",
      "Apache-2.0",
      "https://raw.githubusercontent.com/OpenADMET/openadmet-models/main/LICENSE",
    ],
    [
      "db-pk-db",
      "MIT",
      "https://raw.githubusercontent.com/matthiaskoenig/pkdb/develop/LICENSE",
    ],
  ])(
    "uses the source-code licence file for %s instead of stale surrounding metadata",
    async (id, name, url) => {
      const [resource] = await loadCatalog(`catalog/resources/${id}.yaml`);
      expect(resource.licenses[0].name).toBe(name);
      expect(
        resource.licenses[0].evidence.map(
          (ref) => resource.evidence.find((entry) => entry.id === ref)?.url,
        ),
      ).toContain(url);
    },
  );

  it("preserves explicitly released SAbDab2 training data as distinct from generic downloads", async () => {
    const [resource] = await loadCatalog("catalog/resources/db-sabdab2.yaml");
    expect(resource.openness.training_data.value).toBe("available");
    expect(
      resource.identifiers.some(
        (entry) => entry.url === "https://doi.org/10.5281/zenodo.20083994",
      ),
    ).toBe(true);
  });

  it("directs L1000 readers to archived public data rather than the retired query service", async () => {
    const [resource] = await loadCatalog(
      "catalog/resources/dataset-connectivity-map-l1000.yaml",
    );
    expect(resource.canonical_url).toBe(
      "https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE92742",
    );
    expect(resource.status.value).toBe("legacy");
    expect(
      resource.identifiers.some((entry) => entry.value === "GSE70138"),
    ).toBe(true);
  });
});
