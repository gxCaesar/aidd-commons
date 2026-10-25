import { execFileSync } from "node:child_process";
import { readFileSync } from "node:fs";
import { join } from "node:path";
import { fileURLToPath } from "node:url";

import { expect, it } from "vitest";

const root = fileURLToPath(new URL("../..", import.meta.url));

interface FigureEntry {
  id: string;
  file: string;
  pdf: string;
  width: number;
  height: number;
  pages: string[];
}

const manifest = JSON.parse(
  readFileSync(join(root, "site/src/data/atlas-figures.json"), "utf8"),
) as { figures: FigureEntry[] };

it("diagnoses valid native pairs and known wrong-size, stale-caption and missing-file defects", () => {
  execFileSync(
    join(root, ".venv/bin/python"),
    ["tests/site/test_atlas_figure_delivery.py"],
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

it("publishes source-bound PNG previews with vector PDFs and accurate dimensions", () => {
  expect(manifest.figures.length).toBeGreaterThan(0);
  for (const figure of manifest.figures) {
    expect(figure.file, figure.id).toMatch(/\.png$/u);
    expect(figure.pdf, figure.id).toBe(figure.file.replace(/\.png$/u, ".pdf"));
    const png = readFileSync(join(root, "site/public/figures", figure.file));
    expect(png.subarray(0, 8).toString("hex"), figure.id).toBe(
      "89504e470d0a1a0a",
    );
    expect(figure.width, figure.id).toBe(png.readUInt32BE(16));
    expect(figure.height, figure.id).toBe(png.readUInt32BE(20));
    const pdf = readFileSync(join(root, "site/public/figures", figure.pdf));
    expect(pdf.subarray(0, 5).toString("ascii"), figure.id).toBe("%PDF-");
  }
  execFileSync(
    join(root, ".venv/bin/python"),
    ["site/scripts/check-site-figures.py"],
    {
      cwd: root,
      stdio: "pipe",
    },
  );
});

it("renders every placed preview as an accessible image with a PDF download", () => {
  for (const figure of manifest.figures) {
    for (const page of figure.pages) {
      const html = readFileSync(
        join(root, "site/dist", page, "index.html"),
        "utf8",
      );
      const block = [...html.matchAll(/<figure\b[^>]*>[\s\S]*?<\/figure>/gu)]
        .map((match) => match[0])
        .find((candidate) =>
          candidate.includes(`data-atlas-figure="${figure.id}"`),
        );
      expect(block, `${page} ${figure.id}`).toBeDefined();
      expect(block).toContain(`/figures/${figure.file}`);
      expect(block).toContain(`width="${figure.width}"`);
      expect(block).toContain(`height="${figure.height}"`);
      expect(block).toMatch(/<img\b[^>]*alt="[^"]+"/u);
      const previewLink = block?.match(
        /<a\b[^>]*>[\s\S]*?<img\b[\s\S]*?<\/a>/u,
      )?.[0];
      expect(
        previewLink,
        `${figure.id}: preview opens its vector PDF`,
      ).toContain(`/figures/${figure.pdf}`);
      expect(block).toContain(`/figures/${figure.pdf}`);
      expect(block).toContain("Download PDF");
      expect(block).not.toContain("<svg");
    }
  }
});
