import { glob, readFile, stat } from "node:fs/promises";
import { basename, extname, join } from "node:path";

export type BrokenInternalLink = {
  from: string;
  href: string;
  output: string;
};

function compareCodePoints(left: string, right: string): number {
  return left < right ? -1 : left > right ? 1 : 0;
}

function anchorHrefs(document: string): string[] {
  return Array.from(
    document.matchAll(/<a\b[^>]*\bhref=(["'])([^"']*)\1/giu),
    (match) => match[2],
  );
}

function isExternalOrNonNavigable(href: string): boolean {
  return (
    href === "" ||
    href.startsWith("#") ||
    /^(?:data|javascript|mailto|tel):/iu.test(href) ||
    href.startsWith("//") ||
    /^https?:/iu.test(href)
  );
}

function outputPathFor(pathname: string): string {
  const route = pathname.replace(/^\/+/, "");
  if (route === "") {
    return "index.html";
  }
  if (extname(basename(route)) !== "") {
    return route;
  }
  return `${route.replace(/\/?$/u, "/")}index.html`;
}

export async function findBrokenInternalLinks(
  siteBuildDirectory: string,
  base = "/",
): Promise<BrokenInternalLink[]> {
  const prefix = base.replace(/\/+$/u, "");
  const pages: string[] = [];
  for await (const page of glob("**/*.html", { cwd: siteBuildDirectory })) {
    pages.push(page);
  }

  const brokenLinks: BrokenInternalLink[] = [];
  for (const page of pages.sort(compareCodePoints)) {
    const document = await readFile(join(siteBuildDirectory, page), "utf8");
    for (const href of anchorHrefs(document)) {
      if (isExternalOrNonNavigable(href)) {
        continue;
      }

      const url = new URL(
        href,
        `https://aidd-commons.invalid${prefix}/${page}`,
      );
      if (url.origin !== "https://aidd-commons.invalid") {
        continue;
      }
      if (
        prefix !== "" &&
        url.pathname !== prefix &&
        !url.pathname.startsWith(`${prefix}/`)
      ) {
        brokenLinks.push({
          from: `/${page}`,
          href,
          output: `outside deployment base ${prefix}/`,
        });
        continue;
      }
      const output = outputPathFor(url.pathname.slice(prefix.length));

      try {
        await stat(join(siteBuildDirectory, output));
      } catch {
        brokenLinks.push({ from: `/${page}`, href, output });
      }
    }
  }

  return brokenLinks.sort((left, right) =>
    compareCodePoints(
      `${left.from}\u0000${left.href}`,
      `${right.from}\u0000${right.href}`,
    ),
  );
}

async function main(): Promise<void> {
  const [siteBuildDirectory = "site/dist", base = "/"] = process.argv.slice(2);
  const brokenLinks = await findBrokenInternalLinks(siteBuildDirectory, base);

  if (brokenLinks.length > 0) {
    for (const link of brokenLinks) {
      console.error(`${link.from}: ${link.href} -> ${link.output}`);
    }
    process.exitCode = 1;
    return;
  }

  console.log("Built internal links resolve.");
}

const invokedAsCli =
  process.argv[1] !== undefined &&
  basename(process.argv[1]) === "check-internal-links.ts";

if (invokedAsCli) {
  main().catch((error: unknown) => {
    console.error(error instanceof Error ? error.message : String(error));
    process.exitCode = 1;
  });
}
