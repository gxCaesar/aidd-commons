import { describe, expect, it } from "vitest";
import { loadCatalog } from "../../scripts/catalog/catalog.js";
import { loadCurriculum } from "../../scripts/curriculum/curriculum.js";
import { buildResourceMap } from "../../scripts/curriculum/resource-map.js";

describe("generation resource identity in teaching exports", () => {
  it("resolves the current generation introduction to REINVENT 4 without replacing the archived 3.2 record", async () => {
    const resources = await loadCatalog("catalog/resources");
    const curriculum = await loadCurriculum("catalog/curriculum/tracks.yaml", {
      resources,
    });
    const map = buildResourceMap(curriculum, resources);
    const generation = map.rows.filter(
      (row) => row.lesson_id === "molecular-generation/generation-and-search",
    );
    expect(generation.length).toBeGreaterThan(0);
    for (const row of generation) {
      const urls = row.lesson_resource_ids.map(
        (id) =>
          map.resources.find((resource) => resource.id === id)?.canonical_url,
      );
      expect(urls).toContain("https://github.com/MolecularAI/REINVENT4");
    }
    expect(resources.find(({ id }) => id === "model-reinvent-3")).toMatchObject(
      {
        canonical_url: "https://github.com/MolecularAI/Reinvent",
        status: { value: "legacy" },
      },
    );
  });
});
