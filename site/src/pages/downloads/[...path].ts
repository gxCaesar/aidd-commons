import type { APIRoute } from "astro";
import { labDownloads } from "../../data/lab-downloads.js";

export function getStaticPaths() {
  return labDownloads.map((artifact) => ({
    params: { path: artifact.path },
    props: { artifact },
  }));
}

export const GET: APIRoute = ({ props }) => {
  const artifact = props.artifact as (typeof labDownloads)[number];
  return new Response(artifact.content, {
    headers: {
      "Content-Type": "text/plain; charset=utf-8",
      "Content-Disposition": `attachment; filename="${artifact.path.split("/").at(-1)}"`,
    },
  });
};
