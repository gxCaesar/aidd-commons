import { withoutSiteBase } from "./site-paths.js";

interface LessonFeedbackContext {
  pathname: string;
  base: string;
  lessonId: string;
  publicSiteUrl: string;
  repositoryUrl: string;
  sourceRevision?: string;
  githubSha?: string;
  version: string;
}

/** Construct drafts only; this helper never contacts GitHub or submits feedback. */
export function lessonFeedbackLinks(context: LessonFeedbackContext) {
  const site = new URL(context.publicSiteUrl);
  if (
    site.protocol !== "https:" ||
    ["localhost", "127.0.0.1", "0.0.0.0", "[::1]"].includes(site.hostname) ||
    site.hostname.endsWith(".localhost") ||
    site.username ||
    site.password ||
    site.search ||
    site.hash
  ) {
    throw new Error("Lesson feedback requires the public HTTPS site URL.");
  }
  const repository = new URL(context.repositoryUrl);
  if (
    repository.origin !== "https://github.com" ||
    !/^\/[\w.-]+\/[\w.-]+\/?$/u.test(repository.pathname) ||
    repository.username ||
    repository.password ||
    repository.search ||
    repository.hash
  ) {
    throw new Error(
      "Lesson feedback requires the public GitHub repository URL.",
    );
  }
  if (!context.pathname.startsWith("/") || context.pathname.startsWith("//")) {
    throw new Error("Lesson feedback requires a public lesson pathname.");
  }
  // Use the route only; the preview origin, query and fragment are never included.
  const pathname = new URL(context.pathname, "https://route.invalid").pathname;
  const route = withoutSiteBase(pathname, context.base);
  if (!/^\/(?:zh-cn\/)?(?:learn\/.*)?$/u.test(route)) {
    throw new Error("Lesson feedback requires a public lesson pathname.");
  }
  if (!/^[a-z\d-]+(?:\/[a-z\d-]+)*$/u.test(context.lessonId)) {
    throw new Error(
      "Lesson feedback requires a single-line lesson identifier.",
    );
  }
  const revision =
    context.sourceRevision?.trim() ||
    context.githubSha?.trim() ||
    `v${context.version}`;
  if (
    !/^(?:[a-f\d]{40}|v\d+\.\d+\.\d+(?:-[\w.-]+)?(?:\+[\w.-]+)?)$/iu.test(
      revision,
    )
  ) {
    throw new Error(
      "Lesson feedback requires a source commit or semantic version, not a moving branch.",
    );
  }
  site.pathname = `${site.pathname.replace(/\/+$/u, "")}/`;
  const pageUrl = new URL(route.slice(1), site).href;
  const location = `page=${pageUrl} | lessonId=${context.lessonId} | build source=${revision}`;
  const issueUrl = (template: string) => {
    const url = new URL(
      `${repository.pathname.replace(/\/+$/u, "")}/issues/new`,
      repository,
    );
    url.search = new URLSearchParams({ template, location }).toString();
    return url.href;
  };
  return {
    chinese: route.startsWith("/zh-cn/"),
    pageUrl,
    revision,
    location,
    questionUrl: issueUrl("learning-question.yml"),
    correctionUrl: issueUrl("correction.yml"),
  };
}
