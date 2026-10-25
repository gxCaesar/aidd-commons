import { readFile } from "node:fs/promises";
import { join } from "node:path";
import { fileURLToPath } from "node:url";

import { describe, expect, it } from "vitest";

import { learningTracks } from "../../site/src/data/tracks.js";
import { loadCatalog } from "../../scripts/catalog/catalog.js";

const repositoryRoot = fileURLToPath(new URL("../..", import.meta.url));

const directClaimAccessUrls: Record<string, string[]> = {
  "dataset-rmd17": [],
  "model-alphafold-3-inference": [
    "https://raw.githubusercontent.com/google-deepmind/alphafold3/main/README.md",
  ],
  "model-boltz-1": [
    "https://raw.githubusercontent.com/jwohlwend/boltz/main/LICENSE",
    "https://raw.githubusercontent.com/jwohlwend/boltz/main/README.md",
  ],
  "model-boltz-2": [
    "https://raw.githubusercontent.com/jwohlwend/boltz/main/LICENSE",
    "https://raw.githubusercontent.com/jwohlwend/boltz/main/README.md",
  ],
  "model-chai-1": [
    "https://raw.githubusercontent.com/chaidiscovery/chai-lab/main/LICENSE",
    "https://raw.githubusercontent.com/chaidiscovery/chai-lab/main/README.md",
  ],
  "model-chai-2": ["https://www.chaidiscovery.com/product"],
  "model-isodde": [
    "https://www.isomorphiclabs.com/press/isomorphic-labs-funding",
  ],
  "model-opendde": [
    "https://raw.githubusercontent.com/aurekaresearch/OpenDDE/main/LICENSE",
    "https://raw.githubusercontent.com/aurekaresearch/OpenDDE/main/README.md",
  ],
  "model-openfold": [
    "https://raw.githubusercontent.com/aqlaboratory/openfold/main/LICENSE",
    "https://raw.githubusercontent.com/aqlaboratory/openfold/main/README.md",
  ],
  "model-protenix": [
    "https://raw.githubusercontent.com/bytedance/Protenix/main/LICENSE",
    "https://raw.githubusercontent.com/bytedance/Protenix/main/README.md",
  ],
};

const licenceSourceUrls: Record<string, string> = {
  "dataset-rmd17": "https://doi.org/10.6084/m9.figshare.12672038.v4",
  "model-alphafold-3-inference":
    "https://raw.githubusercontent.com/google-deepmind/alphafold3/main/LICENSE",
  "model-boltz-1":
    "https://raw.githubusercontent.com/jwohlwend/boltz/main/LICENSE",
  "model-boltz-2":
    "https://raw.githubusercontent.com/jwohlwend/boltz/main/LICENSE",
  "model-chai-1":
    "https://raw.githubusercontent.com/chaidiscovery/chai-lab/main/LICENSE",
  "model-opendde":
    "https://raw.githubusercontent.com/aurekaresearch/OpenDDE/main/LICENSE",
  "model-openfold":
    "https://raw.githubusercontent.com/aqlaboratory/openfold/main/LICENSE",
  "model-protenix":
    "https://raw.githubusercontent.com/bytedance/Protenix/main/LICENSE",
};

// The date each pinned access URL was last read. A record that is re-reviewed
// updates this table, so the pinning stays deliberate.
const directClaimReviewedOn: Record<string, string> = {
  "dataset-rmd17": "2026-09-05",
  "model-alphafold-3-inference": "2026-09-04",
  "model-boltz-1": "2026-10-21",
  "model-boltz-2": "2026-10-23",
  "model-chai-1": "2026-10-21",
  "model-chai-2": "2026-10-23",
  "model-isodde": "2026-10-23",
  "model-opendde": "2026-09-04",
  "model-openfold": "2026-09-04",
  "model-protenix": "2026-10-21",


};

describe("Task 3 content and direct-claim evidence", () => {
  it("preserves the original frontier tranche's adjacent primary asset evidence", async () => {
    const resources = await loadCatalog("catalog/resources");
    const ids = new Set(resources.map((resource) => resource.id));
    const directClaimResources = resources.filter((resource) =>
      Object.hasOwn(directClaimAccessUrls, resource.id),
    );

    expect(directClaimResources.map(({ id }) => id).sort()).toEqual(
      Object.keys(directClaimAccessUrls).sort(),
    );
    expect(ids.has("db-pdbbind")).toBe(false);
    expect(ids.has("platform-open-targets")).toBe(false);
    // Every record the project itself points at is pinned to the date its
    // access URL was last read, so a re-review has to be a deliberate edit
    // of this table rather than a silent drift in the registry.
    for (const resource of directClaimResources) {
      expect(resource.last_verified).toBe(
        directClaimReviewedOn[resource.id],
      );
    }
    expect(
      resources.find(({ id }) => id === "dataset-rmd17")?.last_verified,
    ).toBe("2026-09-05");
    expect(
      directClaimResources.every(
        (resource) => resource.status.value === "unverified",
      ),
    ).toBe(true);

    for (const resource of directClaimResources) {
      const evidenceById = new Map(
        resource.evidence.map((evidence) => [evidence.id, evidence]),
      );
      const accessUrls = (resource.access_level.evidence ?? [])
        .map((id) => evidenceById.get(id)?.url)
        .sort();
      expect(accessUrls).toEqual(directClaimAccessUrls[resource.id].sort());

      for (const claim of Object.values(resource.openness)) {
        if (claim.value === "unverified") continue;
        const urls = (claim.evidence ?? []).map(
          (id) => evidenceById.get(id)?.url,
        );
        expect(
          urls.every((url) =>
            url?.startsWith("https://raw.githubusercontent.com/"),
          ),
        ).toBe(true);
      }

      const licenceEvidenceUrls = resource.licenses.flatMap((license) =>
        license.evidence.map((id) => evidenceById.get(id)?.url),
      );
      if (licenceEvidenceUrls.length > 0) {
        expect(licenceEvidenceUrls).toContain(licenceSourceUrls[resource.id]);
        expect(
          licenceEvidenceUrls.every(
            (url) =>
              url?.startsWith("https://raw.githubusercontent.com/") ||
              (resource.id === "dataset-rmd17" &&
                url === "https://doi.org/10.6084/m9.figshare.12672038.v4"),
          ),
        ).toBe(true);
      }

      for (const relation of resource.relations) {
        expect(ids.has(relation.target)).toBe(true);
      }
    }
  });

  it("makes both vertical slices and all Chinese pathway entries concrete", async () => {
    const cofolding = await readFile(
      join(
        repositoryRoot,
        "site/src/content/docs/atlas/open-cofolding-frontier.mdx",
      ),
      "utf8",
    );
    const targetToCandidate = await readFile(
      join(
        repositoryRoot,
        "site/src/content/docs/atlas/target-to-candidate-map.mdx",
      ),
      "utf8",
    );
    const pathwaysIndex = await readFile(
      join(repositoryRoot, "site/src/content/docs/zh-cn/pathways/index.mdx"),
      "utf8",
    );

    for (const dimension of [
      "Inference code",
      "Training code",
      "Weights",
      "Architecture",
      "Data recipe",
      "Training data",
      "Evaluation code",
    ]) {
      expect(cofolding).toContain(dimension);
    }
    for (const system of [
      "Chai-1",
      "Chai-2",
      "AlphaFold 3",
      "IsoDDE",
      "Boltz-1",
      "Boltz-2",
      "OpenFold",
      "Protenix",
      "OpenDDE",
    ]) {
      const row = cofolding
        .split("\n")
        .find((line) => line.startsWith(`| ${system}`));
      expect(row, `${system} needs a cited openness row`).toBeDefined();
      expect(row).toMatch(/\[[^\]]+\]/);
    }
    expect(cofolding).toContain("not a predictive-performance ranking");
    for (const stage of [
      "Disease mechanism",
      "Target hypothesis",
      "Hit discovery",
      "Hit-to-lead",
      "Lead optimization",
      "DMPK and toxicology",
      "Candidate nomination",
    ]) {
      expect(targetToCandidate).toContain(stage);
    }
    for (const heading of [
      "Decision unit",
      "Required evidence",
      "AI tasks",
      "Experimental feedback",
      "Failure gate",
    ]) {
      expect(targetToCandidate).toContain(heading);
    }

    for (const track of learningTracks) {
      expect(pathwaysIndex).toContain(`./${track.id}/`);
      const pathway = await readFile(
        join(
          repositoryRoot,
          "site/src/content/docs/zh-cn/pathways",
          `${track.id}.mdx`,
        ),
        "utf8",
      );
      expect(pathway).toContain("路径摘要");
      expect(pathway).toContain(`/learn/${track.id}/${track.lesson}/`);
    }
  });
});
