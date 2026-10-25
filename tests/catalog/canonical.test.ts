import { describe, expect, it } from "vitest";

import { loadCatalog } from "../../scripts/catalog/catalog.js";

describe("canonical catalog", () => {
  it("contains the source-grounded FreeSolv v0.52 record", async () => {
    const resources = await loadCatalog("catalog/resources");

    expect(resources.length).toBeGreaterThanOrEqual(100);

    const resource = resources.find(({ id }) => id === "freesolv-v0-52");
    expect(resource).toBeDefined();
    expect(resource).toMatchObject({
      id: "freesolv-v0-52",
      name: "FreeSolv v0.52",
      kind: "dataset",
      summary: "Versioned hydration free-energy dataset.",
      canonical_url: "https://github.com/MobleyLab/FreeSolv",
      status: { value: "unverified" },
      access_level: {
        value: "source_available",
        evidence: ["pinned-data", "branch-licence-statement"],
      },
    });
    // The pinned version's own terms are still not established, and the record
    // says so in its first caveat. The licence files on the repository's
    // current branch are a fact about that branch, not about this version.
    expect(resource?.caveats[0]).toContain(
      "The v0.52 release metadata does not declare licence terms; master branch licences are not evidence for this version.",
    );
    expect(resource?.caveats[0]).toContain(
      "The pinned v0.52 tag carries neither file nor a licence section in its README",
    );
    expect(resource?.identifiers).toEqual([
      {
        scheme: "release-doi",
        value: "10.5281/zenodo.1161245",
        url: "https://doi.org/10.5281/zenodo.1161245",
      },
      {
        scheme: "pinned-data",
        value: "v0.52/database.txt",
        url: "https://raw.githubusercontent.com/MobleyLab/FreeSolv/v0.52/database.txt",
      },
    ]);
    expect(resource?.licenses).toEqual([]);
    expect(resource?.evidence.map((evidence) => evidence.url)).toEqual([
      "https://github.com/MobleyLab/FreeSolv",
      "https://raw.githubusercontent.com/MobleyLab/FreeSolv/v0.52/database.txt",
      "https://doi.org/10.5281/zenodo.1161245",
      "https://raw.githubusercontent.com/MobleyLab/FreeSolv/master/README.md",
      "https://raw.githubusercontent.com/MobleyLab/FreeSolv/master/LICENSE",
      "https://raw.githubusercontent.com/MobleyLab/FreeSolv/master/LICENSE_code",
    ]);
    expect(
      resource?.evidence.find((evidence) => evidence.id === "pinned-data")
        ?.supports,
    ).toEqual(["name", "summary", "identifiers", "caveats"]);
    expect(
      resource?.evidence.find((evidence) => evidence.id === "release-doi")
        ?.supports,
    ).toEqual(["identifiers", "caveats"]);
    expect(Object.values(resource!.openness).map(({ value }) => value)).toEqual(
      [
        "not_applicable",
        "not_applicable",
        "not_applicable",
        "not_applicable",
        "available",
        "unverified",
        "not_applicable",
      ],
    );
  });
});
