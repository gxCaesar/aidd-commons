import { readFileSync } from "node:fs";
import { resolve } from "node:path";

import { describe, expect, it } from "vitest";
import { parse } from "yaml";

import { lessonFeedbackLinks } from "../../site/src/lib/lesson-feedback.js";

const root = resolve(import.meta.dirname, "../..");
const invalidContexts = JSON.parse(
  readFileSync(
    resolve(root, "tests/release/fixtures/known-bad/lesson-feedback/paths.json"),
    "utf8",
  ),
) as { publicSiteUrls: string[]; pathnames: string[] };
const commit = "a".repeat(40);
const context = {
  pathname: "/learn/foundations/getting-started/",
  base: "/",
  lessonId: "foundations/getting-started",
  publicSiteUrl: "https://gxcaesar.github.io/aidd-commons/",
  repositoryUrl: "https://github.com/gxCaesar/aidd-commons",
  sourceRevision: commit,
  version: "0.3.0",
};

describe("lesson feedback drafts", () => {
  it.each([
    [
      "/",
      "/learn/foundations/getting-started/",
      "learn/foundations/getting-started/",
      false,
    ],
    [
      "/",
      "/zh-cn/learn/foundations/getting-started/",
      "zh-cn/learn/foundations/getting-started/",
      true,
    ],
    [
      "/aidd-commons/",
      "/aidd-commons/learn/foundations/getting-started/",
      "learn/foundations/getting-started/",
      false,
    ],
    [
      "/aidd-commons",
      "/aidd-commons/zh-cn/learn/foundations/getting-started/",
      "zh-cn/learn/foundations/getting-started/",
      true,
    ],
    ["/", "/", "", false],
    ["/aidd-commons/", "/aidd-commons", "", false],
    ["/aidd-commons/", "/aidd-commons/zh-cn/", "zh-cn/", true],
  ])(
    "keeps the public route and language at base %s and pathname %s",
    (base, pathname, relative, chinese) => {
      const result = lessonFeedbackLinks({
        ...context,
        base: String(base),
        pathname: String(pathname),
      });
      expect(result.pageUrl).toBe(`${context.publicSiteUrl}${relative}`);
      expect(result.chinese).toBe(chinese);
      expect(result.pageUrl).not.toContain("aidd-commons/aidd-commons");
    },
  );

  it("also supports a public site mounted at its host root and strips preview query context", () => {
    const result = lessonFeedbackLinks({
      ...context,
      publicSiteUrl: "https://learn.example.org",
      pathname: `${context.pathname}?preview=http://localhost:4321#private-note`,
    });
    expect(result.pageUrl).toBe(`https://learn.example.org${context.pathname}`);
    expect(result.location).not.toMatch(/localhost|private-note|preview=/u);
  });

  it("prefills the actual location field in both issue forms as a single line", () => {
    const result = lessonFeedbackLinks(context);
    for (const [href, template] of [
      [result.questionUrl, "learning-question.yml"],
      [result.correctionUrl, "correction.yml"],
    ]) {
      const url = new URL(href!);
      expect(`${url.origin}${url.pathname}`).toBe(
        `${context.repositoryUrl}/issues/new`,
      );
      expect(url.searchParams.get("template")).toBe(template);
      const location = url.searchParams.get("location")!;
      expect(location).toBe(result.location);
      expect(location).toContain(`page=${result.pageUrl}`);
      expect(location).toContain(`lessonId=${context.lessonId}`);
      expect(location).toContain(`build source=${commit}`);
      expect(location).not.toMatch(/[\r\n]|localhost|file:\/\/|\/Users\//u);
      const form = parse(
        readFileSync(
          resolve(root, ".github/ISSUE_TEMPLATE", template!),
          "utf8",
        ),
      );
      expect(
        form.body.find((field: { id?: string }) => field.id === "location")
          .type,
      ).toBe("input");
    }
  });

  it("prioritizes explicit build source, then GitHub commit, then manifest semantic version", () => {
    const githubSha = "b".repeat(40);
    expect(lessonFeedbackLinks({ ...context, githubSha }).revision).toBe(
      commit,
    );
    expect(
      lessonFeedbackLinks({ ...context, sourceRevision: " ", githubSha })
        .revision,
    ).toBe(githubSha);
    const manifest = JSON.parse(
      readFileSync(resolve(root, "package.json"), "utf8"),
    );
    expect(
      lessonFeedbackLinks({
        ...context,
        sourceRevision: undefined,
        version: manifest.version,
      }).revision,
    ).toBe(`v${manifest.version}`);
    expect(
      lessonFeedbackLinks({ ...context, sourceRevision: "v0.3.0-rc.1" })
        .revision,
    ).toBe("v0.3.0-rc.1");
  });

  it.each(["main", "refs/heads/main", "../../main", "", "v0.3"])(
    "rejects an unversioned or invalid source %s",
    (revision) => {
      const options =
        revision === ""
          ? { ...context, sourceRevision: undefined, version: "main" }
          : { ...context, sourceRevision: revision };
      expect(() => lessonFeedbackLinks(options)).toThrow(
        "source commit or semantic version",
      );
    },
  );

  it("rejects local origins, filesystem paths and multiline identifiers rather than leaking them", () => {
    for (const publicSiteUrl of invalidContexts.publicSiteUrls) {
      expect(() => lessonFeedbackLinks({ ...context, publicSiteUrl })).toThrow(
        "public HTTPS",
      );
    }
    for (const pathname of invalidContexts.pathnames) {
      expect(() => lessonFeedbackLinks({ ...context, pathname })).toThrow(
        "public lesson pathname",
      );
    }
    expect(() =>
      lessonFeedbackLinks({
        ...context,
        lessonId: "foundations/example\nprivate",
      }),
    ).toThrow("single-line lesson identifier");
    expect(() =>
      lessonFeedbackLinks({
        ...context,
        repositoryUrl: "https://example.org/owner/repository",
      }),
    ).toThrow("public GitHub");
  });
});

describe("lesson feedback integration", () => {
  it("adds only optional location context while retaining all six required correction evidence fields", () => {
    const form = parse(
      readFileSync(
        resolve(root, ".github/ISSUE_TEMPLATE/correction.yml"),
        "utf8",
      ),
    );
    const required = form.body.filter(
      (field: { validations?: { required?: boolean } }) =>
        field.validations?.required,
    );
    expect(required.map((field: { id: string }) => field.id)).toEqual([
      "summary",
      "evidence",
      "licence_attribution",
      "audience",
      "scientific_assumptions",
      "conflict_disclosure",
    ]);
    expect(
      required.every((field: { type: string }) => field.type === "textarea"),
    ).toBe(true);
    expect(
      form.body.find((field: { id: string }) => field.id === "location")
        .validations.required,
    ).toBe(false);
  });

  it("places visible localized static links on every LessonProgress page without changing progress or resource controls", () => {
    const component = readFileSync(
      resolve(root, "site/src/components/LessonFeedback.astro"),
      "utf8",
    );
    const progress = readFileSync(
      resolve(root, "site/src/components/LessonProgress.astro"),
      "utf8",
    );
    expect(progress).toContain("<LessonFeedback lessonId={lessonId} />");
    expect(progress).toContain("<LessonResources lessonId={lessonId} />");
    expect(progress).toContain("readLessonProgress(localStorage)");
    expect(progress).toContain(
      "toggleLessonProgress(this.completed, lessonId)",
    );
    expect(component).toContain("href={feedback.questionUrl}");
    expect(component).toContain("href={feedback.correctionUrl}");
    for (const label of [
      "Ask about this lesson",
      "本课提问",
      "Report a correction",
      "反馈错误",
    ]) {
      expect(component).toContain(label);
    }
    expect(component).toContain("Posting requires a GitHub sign-in");
    expect(component).toContain("no post is sent automatically");
    expect(component).toContain("Reading needs no account");
    expect(component).toContain("发帖需要登录 GitHub");
    expect(component).toContain("不会自动发帖");
    expect(component).toContain("阅读本课无需账号");
    expect(component).toContain("min-height: 44px");
    expect(component).toContain("flex-wrap: wrap");
    expect(component).toContain("publication.site_url");
    expect(component).toContain("process.env.AIDD_SOURCE_REVISION");
    expect(component).toContain("process.env.GITHUB_SHA");
    expect(component).toContain("version: manifest.version");
    expect(component).not.toMatch(
      /<script\b|<form\b|fetch\(|Astro\.url\.(?:origin|href)/u,
    );
  });
});
