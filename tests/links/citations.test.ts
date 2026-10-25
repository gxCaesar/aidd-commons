import { mkdir, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { mkdtemp } from "node:fs/promises";

import { describe, expect, it } from "vitest";

describe("citation key checker", () => {
  it("reports citation keys absent from the bibliography", async () => {
    const { findUnresolvedCitationKeys } = await import(
      "../../scripts/quality/check-citations.js"
    );
    const directory = await mkdtemp(join(tmpdir(), "aidd-citations-"));
    const reportPath = join(directory, "report.md");
    const bibliographyPath = join(directory, "references.bib");
    await mkdir(directory, { recursive: true });
    await Promise.all([
      writeFile(reportPath, "Known [@known] and missing [@missing].\n"),
      writeFile(bibliographyPath, "@article{known,\n  title = {Known}\n}\n"),
    ]);

    await expect(
      findUnresolvedCitationKeys(reportPath, bibliographyPath),
    ).resolves.toEqual(["missing"]);
  });
});
