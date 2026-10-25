import { readFile } from "node:fs/promises";
import { parse } from "yaml";
import type { Resource } from "../../../../catalog/schema/resource.js";
import type { Curriculum } from "../../../../scripts/curriculum/curriculum.js";
import { buildResourceMap } from "../../../../scripts/curriculum/resource-map.js";
import resourceData from "../../../public/data/resources.v1.json";

export async function GET() {
  const curriculum = parse(await readFile(
    new URL("../../../../catalog/curriculum/tracks.yaml", import.meta.url), "utf8",
  )) as Curriculum;
  return new Response(JSON.stringify(buildResourceMap(curriculum, resourceData as Resource[])), {
    headers: { "Content-Type": "application/json" },
  });
}
