/** Keep authored root-relative links usable at a static host's project path. */
export function withSiteBase(path: string, base: string): string {
  const prefix = base.replace(/\/+$/u, "");
  if (
    prefix === "" ||
    !path.startsWith("/") ||
    path.startsWith("//") ||
    path === prefix ||
    path.startsWith(`${prefix}/`)
  ) {
    return path;
  }
  return `${prefix}${path}`;
}

export function withoutSiteBase(path: string, base: string): string {
  const prefix = base.replace(/\/+$/u, "");
  if (prefix !== "" && path === prefix) return "/";
  return prefix !== "" && path.startsWith(`${prefix}/`)
    ? path.slice(prefix.length)
    : path;
}

export function rewriteHtmlSitePaths(html: string, base: string): string {
  if (base.replace(/\/+$/u, "") === "") return html;
  return html.replace(/<[a-z][^>]*>/giu, (tag) =>
    tag.replace(
      /(\s(?:href|src|action|poster)=)(["'])(\/[^"']*)\2/giu,
      (_attribute, name: string, quote: string, path: string) =>
        `${name}${quote}${withSiteBase(path, base)}${quote}`,
    ),
  );
}
