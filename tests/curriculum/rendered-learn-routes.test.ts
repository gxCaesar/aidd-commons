import { readFile, stat } from "node:fs/promises";
import { join } from "node:path";
import { fileURLToPath } from "node:url";

import { describe, expect, it } from "vitest";
import { parse } from "yaml";

import { learningTracks } from "../../site/src/data/tracks.js";

const repositoryRoot = fileURLToPath(new URL("../..", import.meta.url));
const siteBuildDirectory = join(repositoryRoot, "site", "dist");

describe("rendered curriculum Learn routes", () => {
  it("renders an internal canonical route for each of the 18 track introductions", async () => {
    const curriculum = parse(
      await readFile(
        join(repositoryRoot, "catalog", "curriculum", "tracks.yaml"),
        "utf8",
      ),
    ) as {
      tracks: Array<{
        id: string;
        lessons: Array<{ id: string; type: string }>;
      }>;
    };
    const introLessonByTrack = new Map(
      curriculum.tracks.map((track) => [
        track.id,
        track.lessons.find((lesson) => lesson.type === "intro")?.id,
      ]),
    );
    const missing: string[] = [];
    const rendered: string[] = [];

    for (const track of learningTracks) {
      expect(introLessonByTrack.get(track.id)).toBe(track.lesson);
      const href = `/learn/${track.id}/${track.lesson}/`;
      const output = join(
        siteBuildDirectory,
        "learn",
        track.id,
        track.lesson,
        "index.html",
      );
      try {
        const document = await readFile(output, "utf8");
        rendered.push(href);
        expect(document).toContain(track.lessonTitle);
      } catch {
        missing.push(href);
      }
    }

    expect(rendered).toHaveLength(18);
    expect(missing).toEqual([]);
    await stat(
      join(
        siteBuildDirectory,
        "learn",
        "foundations",
        "getting-started",
        "index.html",
      ),
    );
  });
});
