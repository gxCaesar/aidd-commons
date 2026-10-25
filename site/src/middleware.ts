import { defineMiddleware } from "astro:middleware";
import { rewriteHtmlSitePaths } from "./lib/site-paths";

// Markdown, MDX and custom pages share authored root-relative URLs. Rewrite the
// rendered attributes once so the same sources work at / and on GitHub Pages.
export const onRequest = defineMiddleware(async (_context, next) => {
  const response = await next();
  if (!response.headers.get("content-type")?.includes("text/html"))
    return response;
  if (import.meta.env.BASE_URL === "/") return response;
  const headers = new Headers(response.headers);
  headers.delete("content-length");
  return new Response(
    rewriteHtmlSitePaths(await response.text(), import.meta.env.BASE_URL),
    { status: response.status, statusText: response.statusText, headers },
  );
});
