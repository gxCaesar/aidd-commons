import {
  defineRouteMiddleware,
  type StarlightRouteData,
} from "@astrojs/starlight/route-data";
import { withSiteBase, withoutSiteBase } from "./lib/site-paths";

// These custom pages remain canonical English routes, not translated docs.
const canonicalSections = new Set(["atlas", "audit", "report", "contribute"]);
type Entry = StarlightRouteData["sidebar"][number];
function localizeEntry(entry: Entry): Entry {
  if (entry.type === "group")
    return { ...entry, entries: entry.entries.map(localizeEntry) };
  const href = withoutSiteBase(entry.href, import.meta.env.BASE_URL);
  const section = href.split("/")[2];
  return href.startsWith("/zh-cn/") && canonicalSections.has(section)
    ? {
        ...entry,
        href: withSiteBase(
          href.replace(/^\/zh-cn/, ""),
          import.meta.env.BASE_URL,
        ),
      }
    : entry;
}

export const onRequest = defineRouteMiddleware((context) => {
  const route = context.locals.starlightRoute;
  if (route.locale !== "zh-cn") return;
  route.sidebar = route.sidebar.map(localizeEntry);
  for (const direction of ["prev", "next"] as const) {
    const entry = route.pagination[direction];
    if (entry)
      route.pagination[direction] = localizeEntry(entry) as typeof entry;
  }
});
