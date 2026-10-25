import { existsSync, readFileSync, readdirSync } from 'node:fs';
import { resolve } from 'node:path';

import { describe, expect, it } from 'vitest';

const root = resolve(import.meta.dirname, '../..');
const reportDir = resolve(root, 'report');
const figuresDir = resolve(reportDir, 'figures');
const outDir = resolve(figuresDir, 'out');
const buildPath = resolve(reportDir, 'build.sh');
const metadataPath = resolve(reportDir, 'metadata.yaml');

/** The manifests the generators write their captions into. */
const manifests = {
  plots: JSON.parse(readFileSync(resolve(outDir, 'captions.json'), 'utf8')) as Record<string, string>,
  schematics: JSON.parse(
    readFileSync(resolve(outDir, 'captions-schematics.json'), 'utf8'),
  ) as Record<string, string>,
};

/** The files a figure may be written under. */
const productSuffixes = ['.pdf', '.png', '.svg'];

/** The files in the output directory that are a manifest rather than a product. */
const manifestNames = ['captions.json', 'captions-schematics.json', 'palette-cvd.json'];

/**
 * The stem each generator writes, read from the generator itself rather than guessed
 * from the files on disk, so that a figure that has gone missing is reported as
 * missing instead of quietly dropping out of the check.
 */
function generatorStems(): Map<string, string> {
  const stems = new Map<string, string>();

  for (const name of readdirSync(figuresDir)) {
    if (!name.endsWith('.py')) continue;
    const source = readFileSync(resolve(figuresDir, name), 'utf8');
    const stem = /^STEM = "([^"]+)"/m.exec(source)?.[1];
    if (stem === undefined) continue;

    const plotNumber = /^FIGURE_NUMBER = (\d+)$/m.exec(source)?.[1];
    const schematicIndex = /^schematic-(\d+)-/.exec(stem)?.[1];

    if (plotNumber !== undefined && /^plot_\d+_/.test(stem)) {
      stems.set(plotNumber, stem);
    } else if (schematicIndex !== undefined) {
      stems.set(`S${Number(schematicIndex)}`, stem);
    }
  }

  return stems;
}

/** The caption key every product on disk belongs under, or undefined when it has none. */
function captionKeyFor(stem: string): string | undefined {
  const plot = /^plot_(\d+)_/.exec(stem);
  if (plot) return plot[1];

  const schematic = /^schematic-(\d+)-/.exec(stem);
  if (schematic) return `S${Number(schematic[1])}`;

  return undefined;
}

/** The resource directories the build hands to Pandoc, read from the build script. */
function resourcePathEntries(source: string): string[] {
  const match = /--resource-path[=\s]+"?([^"\s]+)"?/.exec(source);
  return match === null ? [] : match[1].split(':').filter(Boolean);
}

const stems = generatorStems();
const buildSource = readFileSync(buildPath, 'utf8');
const metadataSource = readFileSync(metadataPath, 'utf8');

describe('report figure manifest', () => {
  it('gives every captioned figure a vector file and a raster file on disk', () => {
    const missing: string[] = [];

    for (const [key, stem] of stems) {
      for (const suffix of ['.pdf', '.png']) {
        if (!existsSync(resolve(outDir, `${stem}${suffix}`))) {
          missing.push(`${stem}${suffix}, the ${key} caption`);
        }
      }
    }

    expect(missing).toEqual([]);
    expect(stems.size).toBe(
      Object.keys(manifests.plots).length + Object.keys(manifests.schematics).length,
    );
  });

  it('gives every figure on disk a caption, and every caption a generator', () => {
    const uncaptioned: string[] = [];
    const withoutGenerator: string[] = [];

    for (const name of readdirSync(outDir)) {
      if (!productSuffixes.some((suffix) => name.endsWith(suffix))) continue;
      const stem = name.slice(0, name.lastIndexOf('.'));
      const key = captionKeyFor(stem);
      const table = key !== undefined && key.startsWith('S') ? manifests.schematics : manifests.plots;
      if (key === undefined || table[key] === undefined) uncaptioned.push(name);
    }

    for (const key of [...Object.keys(manifests.plots), ...Object.keys(manifests.schematics)]) {
      if (!stems.has(key)) withoutGenerator.push(key);
    }

    expect(uncaptioned).toEqual([]);
    expect(withoutGenerator).toEqual([]);
  });

  it('keeps the figure directory to generators, products and manifests', () => {
    const unexpected: string[] = [];

    for (const entry of readdirSync(figuresDir, { withFileTypes: true })) {
      // Python's bytecode cache is not a checked artefact, is not tracked, and is
      // excluded from the public export by name.
      if (entry.name === '__pycache__') continue;

      if (entry.isDirectory()) {
        if (entry.name !== 'out') unexpected.push(`${entry.name}/`);
        continue;
      }

      if (entry.name.startsWith('.')) continue;
      if (!entry.name.endsWith('.py')) unexpected.push(entry.name);
    }

    for (const name of readdirSync(outDir)) {
      if (manifestNames.includes(name)) continue;
      if (!productSuffixes.some((suffix) => name.endsWith(suffix))) unexpected.push(`out/${name}`);
    }

    expect(unexpected).toEqual([]);
  });

  it('draws the figures before the document and hands Pandoc the figure directory', () => {
    expect(buildSource).toContain('build_figures.py');
    expect(buildSource.indexOf('build_figures.py')).toBeLessThan(buildSource.indexOf('pandoc'));

    const entries = resourcePathEntries(buildSource);
    expect(entries).not.toEqual([]);

    const unreachable: string[] = [];
    for (const stem of stems.values()) {
      const found = entries.some((entry) =>
        existsSync(resolve(reportDir, entry, `${stem}.pdf`)),
      );
      if (!found) unreachable.push(stem);
    }

    expect(unreachable).toEqual([]);
  });

  it('declares the packages and the settings a figure include needs', () => {
    expect(metadataSource).toContain('graphicx');
    expect(metadataSource).toContain('caption');
    expect(metadataSource).toContain('captionsetup');
    expect(metadataSource).toMatch(/\\setkeys\{Gin\}/);
    expect(metadataSource).toMatch(/width=\\textwidth/);
    expect(metadataSource).toMatch(/keepaspectratio/);
  });

  it('numbers figures and tables as one list rather than restarting them', () => {
    expect(metadataSource).toMatch(/\\@removefromreset\{figure\}\{chapter\}/);
    expect(metadataSource).toMatch(/\\@removefromreset\{table\}\{chapter\}/);
    expect(metadataSource).toMatch(/\\renewcommand\{\\thefigure\}\{\\arabic\{figure\}\}/);
    expect(metadataSource).toMatch(/\\renewcommand\{\\thetable\}\{\\arabic\{table\}\}/);
  });
});
