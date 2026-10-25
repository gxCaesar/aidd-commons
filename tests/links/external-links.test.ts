import { afterEach, describe, expect, it, vi } from "vitest";

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("external link availability report", () => {
  it("extracts unique HTTP URLs without treating them as supported claims", async () => {
    const { externalUrlsFromText } = await import(
      "../../scripts/quality/check-external-links.js"
    );

    expect(
      externalUrlsFromText(
        "See https://example.org/source and https://example.org/source. Ignore /learn/. ",
      ),
    ).toEqual(["https://example.org/source"]);
  });

  it("stops a URL at an adjacent CJK character instead of swallowing the following prose", async () => {
    const { externalUrlsFromText } = await import(
      "../../scripts/quality/check-external-links.js"
    );

    expect(
      externalUrlsFromText(
        "[PoseBusters](https://arxiv.org/abs/2308.05777)（Buttenschoen、Morris 与 Deane）。",
      ),
    ).toEqual(["https://arxiv.org/abs/2308.05777"]);

    expect(
      externalUrlsFromText("见 https://arxiv.org/abs/2107.07511)。相关方法可沿此扩展。"),
    ).toEqual(["https://arxiv.org/abs/2107.07511"]);
  });

  it("records an HTTP response as availability only, never claim support", async () => {
    const { checkExternalUrlAvailability } = await import(
      "../../scripts/quality/check-external-links.js"
    );
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ status: 204 }));

    await expect(
      checkExternalUrlAvailability("https://example.org/source"),
    ).resolves.toEqual({
      availability: "http-response",
      claim_support: "not_assessed",
      status: 204,
      url: "https://example.org/source",
    });
  });
});
