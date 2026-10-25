import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';

import { describe, expect, it } from 'vitest';

const root = resolve(import.meta.dirname, '../..');
const outDir = resolve(root, 'report/figures/out');
const reportPath = resolve(root, 'report/aidd-commons-living-report-v0.1.md');

const plots = JSON.parse(readFileSync(resolve(outDir, 'captions.json'), 'utf8')) as Record<
  string,
  string
>;
const schematics = JSON.parse(
  readFileSync(resolve(outDir, 'captions-schematics.json'), 'utf8'),
) as Record<string, string>;

/** Every figure the document embeds, with the caption it carries in the alt text. */
function embeddedFigures(): { path: string; alt: string }[] {
  const document = readFileSync(reportPath, 'utf8');
  const pattern = /!\[([^\]]*)\]\((figures\/out\/(?:plot_\d+_|schematic-\d+-)[^)]*)\)/g;
  const found: { path: string; alt: string }[] = [];
  for (const match of document.matchAll(pattern)) {
    found.push({ alt: match[1], path: match[2] });
  }
  return found;
}

/** The caption a figure path belongs under in the manifests. */
function captionFor(path: string): string | undefined {
  const plot = /plot_(\d+)_/.exec(path);
  if (plot !== null) return plots[plot[1]];
  const schematic = /schematic-(\d+)-/.exec(path);
  if (schematic !== null) return schematics[`S${Number(schematic[1])}`];
  return undefined;
}

describe('figure captions in the report', () => {
  it('carries the generated caption for every figure it embeds', () => {
    const drift: string[] = [];
    for (const figure of embeddedFigures()) {
      const caption = captionFor(figure.path);
      if (caption === undefined) {
        drift.push(`${figure.path}: no caption in the manifest`);
        continue;
      }
      if (caption.trim() !== figure.alt.trim()) {
        drift.push(`${figure.path}: the caption in the document is not the generated one`);
      }
    }
    expect(drift).toEqual([]);
  });

  it('embeds every figure the manifests carry a caption for', () => {
    const embedded = embeddedFigures().map((figure) => figure.path);
    const missing: string[] = [];
    for (const key of Object.keys(plots)) {
      if ((plots[key] ?? '').length === 0) continue;
      const found = embedded.some((path) => /^figures\/out\/plot_(\d+)_/.test(path) && Number(RegExp.$1) === Number(key));
      if (!found) missing.push(`plot ${key}`);
    }
    for (const key of Object.keys(schematics)) {
      if ((schematics[key] ?? '').length === 0) continue;
      const wanted = Number(key.slice(1));
      const found = embedded.some(
        (path) => /^figures\/out\/schematic-(\d+)-/.test(path) && Number(RegExp.$1) === wanted,
      );
      if (!found) missing.push(`schematic ${key}`);
    }
    expect(missing).toEqual([]);
  });
});
