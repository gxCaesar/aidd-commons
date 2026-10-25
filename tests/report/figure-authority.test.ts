import { execFileSync } from "node:child_process";
import { readFileSync } from "node:fs";
import { join } from "node:path";
import { fileURLToPath } from "node:url";

import { expect, it } from "vitest";

const root = fileURLToPath(new URL("../..", import.meta.url));

it("keeps figure quantities, reading dates and the 93-topic axis within their source authority", () => {
  execFileSync(
    join(root, ".venv/bin/python"),
    ["tests/report/test_figure_authority.py"],
    {
      cwd: root,
      env: {
        ...process.env,
        MPLBACKEND: "Agg",
        MPLCONFIGDIR: process.env.MPLCONFIGDIR || join(root, ".cache", "matplotlib"),
      },
      stdio: "pipe",
    },
  );
}, 60_000); // A first font-cache build can exceed 30 seconds on macOS.

it("keeps the live Atlas figure captions aligned with the canonical projection", () => {
  const resources = JSON.parse(
    readFileSync(join(root, "site/public/data/resources.v1.json"), "utf8"),
  ) as Array<{ last_verified: string }>;
  const captions = JSON.parse(
    readFileSync(join(root, "report/figures/out/captions.json"), "utf8"),
  ) as Record<string, string>;
  expect(
    resources.length,
    "the Atlas projection must not be empty",
  ).toBeGreaterThan(0);
  const dates = resources.map((record) => record.last_verified).sort();
  const patterns: Record<string, RegExp> = {
    "1": /^Registry composition by kind\. (\d+) catalogue records/u,
    "6": /^Openness by record kind and by the seven openness dimensions, over (\d+) catalogue records/u,
    "7": /^Access level and licence layer for the (\d+) catalogue records/u,
  };
  for (const [number, pattern] of Object.entries(patterns)) {
    expect(
      Number(pattern.exec(captions[number])?.[1]),
      `plot ${number} record denominator`,
    ).toBe(resources.length);
    expect(
      captions[number],
      `plot ${number} record verification scope`,
    ).toContain(`verification dates range from ${dates[0]} to ${dates.at(-1)}`);
  }
});
