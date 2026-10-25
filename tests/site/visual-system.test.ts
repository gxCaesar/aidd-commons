import { readFile } from "node:fs/promises";
import { join } from "node:path";
import { fileURLToPath } from "node:url";

import { describe, expect, it } from "vitest";

const repositoryRoot = fileURLToPath(new URL("../..", import.meta.url));

async function read(relativePath: string) {
  return readFile(join(repositoryRoot, relativePath), "utf8");
}

// The house colour-vision floor, written out here so that lowering it in the palette
// module or in the measured record fails this file instead of quietly passing.
const CVD_FLOOR = 10.0;
const CONTRAST_FLOOR = 3.0;

const PINNED_TOKENS = {
  light: {
    bg: "#fbf8f1",
    panel: "#fffdf8",
    ink: "#13283d",
    muted: "#536675",
    rule: "#ccd4d3",
    teal: "#087c78",
    teal_deep: "#075e5c",
    coral: "#c85f51",
    focus: "#e05d44",
  },
  dark: {
    bg: "#10202e",
    panel: "#172b3b",
    ink: "#edf3f2",
    muted: "#b7c6cc",
    rule: "#3d5665",
    teal: "#4fc7bf",
    teal_deep: "#90e4dc",
    coral: "#fc9a88",
    focus: "#ffb15b",
  },
};

const hexPattern = /#[0-9a-f]{6}\b/gi;

function hexesIn(text: string): string[] {
  return [...new Set(text.match(hexPattern) ?? [])]
    .map((value) => value.toLowerCase())
    .sort();
}

function hexesInJson(value: unknown): string[] {
  const found: string[] = [];
  const walk = (node: unknown): void => {
    if (typeof node === "string") {
      found.push(...hexesIn(node));
    } else if (Array.isArray(node)) {
      node.forEach(walk);
    } else if (node !== null && typeof node === "object") {
      Object.values(node as Record<string, unknown>).forEach(walk);
    }
  };
  walk(value);
  return [...new Set(found)].sort();
}

function relativeLuminance(hex: string): number {
  const channels = [1, 3, 5].map((offset) => {
    const value = Number.parseInt(hex.slice(offset, offset + 2), 16) / 255;
    return value <= 0.04045 ? value / 12.92 : ((value + 0.055) / 1.055) ** 2.4;
  });
  return 0.2126 * channels[0] + 0.7152 * channels[1] + 0.0722 * channels[2];
}

function contrastRatio(foreground: string, background: string): number {
  const first = relativeLuminance(foreground);
  const second = relativeLuminance(background);
  const lighter = Math.max(first, second);
  const darker = Math.min(first, second);
  return (lighter + 0.05) / (darker + 0.05);
}

describe("figure palette", () => {
  it("keeps the site mirror and the Python source of truth on the same colours", async () => {
    const [mirror, source] = await Promise.all([
      read("site/src/data/atlas-palette.json"),
      read("report/figures/atlas_palette.py"),
    ]);
    const mirrored = hexesInJson(JSON.parse(mirror));
    const authored = hexesIn(source);

    expect(authored.length).toBeGreaterThan(20);
    expect(mirrored).toEqual(authored);
  });

  it("records a measured worst pair at or above the floor, and keeps the floor itself", async () => {
    const [measured, source] = await Promise.all([
      read("report/figures/out/palette-cvd.json"),
      read("report/figures/atlas_palette.py"),
    ]);
    const record = JSON.parse(measured);

    expect(record.cvd_floor).toBe(CVD_FLOOR);
    expect(record.floors.cvd_ciede2000).toBe(CVD_FLOOR);
    const declared = source.match(/CVD_FLOOR[^=]*=\s*([0-9.]+)/);
    expect(declared).not.toBeNull();
    expect(Number(declared?.[1])).toBe(CVD_FLOOR);

    for (const theme of ["light", "dark"]) {
      const worst = record.themes[theme].worst_pair;
      expect(worst.deutan.distance).toBeGreaterThanOrEqual(CVD_FLOOR);
      expect(worst.protan.distance).toBeGreaterThanOrEqual(CVD_FLOOR);
      expect(record.themes[theme].gates.cvd_pass).toBe(true);
      expect(record.themes[theme].gates.luminance_pass).toBe(true);
      expect(record.themes[theme].gates.contrast_pass).toBe(true);
      expect(record.themes[theme].gates.ladder_pass).toBe(true);
    }
  });

  it("clears 3:1 against the panel each colour is drawn on, in both themes", async () => {
    const mirror = JSON.parse(await read("site/src/data/atlas-palette.json"));
    const tooFaint: string[] = [];

    for (const theme of ["light", "dark"] as const) {
      const { tokens, categorical } = mirror.themes[theme] as {
        tokens: { panel: string };
        categorical: Record<string, string>;
      };
      for (const [name, value] of Object.entries(categorical)) {
        const ratio = contrastRatio(value, tokens.panel);
        if (ratio < CONTRAST_FLOOR) {
          tooFaint.push(
            `${theme} ${name} ${value} on ${tokens.panel}: ${ratio.toFixed(2)}:1`,
          );
        }
      }
    }

    expect(tooFaint).toEqual([]);
  });

  it("carries the nine pinned site tokens verbatim in both implementations", async () => {
    const [mirror, source] = await Promise.all([
      read("site/src/data/atlas-palette.json"),
      read("report/figures/atlas_palette.py"),
    ]);
    const parsed = JSON.parse(mirror);

    for (const theme of ["light", "dark"] as const) {
      expect(parsed.themes[theme].tokens).toEqual(PINNED_TOKENS[theme]);
      expect(Object.keys(PINNED_TOKENS[theme])).toHaveLength(9);
      for (const value of Object.values(PINNED_TOKENS[theme])) {
        expect(source).toContain(`"${value}"`);
      }
    }
  });
});
