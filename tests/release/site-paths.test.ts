import { describe, expect, it } from "vitest";

import {
  rewriteHtmlSitePaths,
  withSiteBase,
  withoutSiteBase,
} from "../../site/src/lib/site-paths.js";

describe("static project paths", () => {
  it("prefixes local routes once and preserves external or in-page URLs", () => {
    expect(withSiteBase("/atlas/?q=protein#results", "/aidd-commons/")).toBe(
      "/aidd-commons/atlas/?q=protein#results",
    );
    expect(withSiteBase("/aidd-commons/atlas/", "/aidd-commons")).toBe(
      "/aidd-commons/atlas/",
    );
    for (const path of [
      "https://example.org/",
      "//example.org/a",
      "#method",
      "../data/file.json",
    ]) {
      expect(withSiteBase(path, "/aidd-commons/")).toBe(path);
    }
    expect(withSiteBase("/labs/", "/")).toBe("/labs/");
  });

  it("detects the locale after removing only the deployment base", () => {
    expect(withoutSiteBase("/aidd-commons/zh-cn/labs/", "/aidd-commons/")).toBe(
      "/zh-cn/labs/",
    );
    expect(withoutSiteBase("/aidd-commons", "/aidd-commons")).toBe("/");
    expect(withoutSiteBase("/other/zh-cn/", "/aidd-commons")).toBe(
      "/other/zh-cn/",
    );
  });

  it("rewrites actual HTML URL attributes without changing prose or third-party assets", () => {
    const html =
      '<a href="/labs/">Lab</a><img src="/figures/a.png"><a href="//example.org/">External</a><a href="/aidd-commons/atlas/">Atlas</a><code>&lt;a href="/example/"&gt;</code>';
    expect(rewriteHtmlSitePaths(html, "/aidd-commons/")).toBe(
      '<a href="/aidd-commons/labs/">Lab</a><img src="/aidd-commons/figures/a.png"><a href="//example.org/">External</a><a href="/aidd-commons/atlas/">Atlas</a><code>&lt;a href="/example/"&gt;</code>',
    );
    expect(rewriteHtmlSitePaths(html, "/")).toBe(html);
  });
});
