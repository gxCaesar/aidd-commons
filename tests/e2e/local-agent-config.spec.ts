import { readFile } from "node:fs/promises";
import { expect, test } from "@playwright/test";

const artifacts = [
  "configs/scientific-agents/paperqa-local.json",
  "scripts/agents/check_local_profile.py",
  "labs/paperqa_local/paperqa_local_tutorial.ipynb",
  "labs/paperqa_local/paperqa_local_tutorial.zh-CN.ipynb",
  "labs/paperqa_local/reviewed-example.json",
];

for (const prefix of ["", "/zh-cn"]) {
  test(`local configuration downloads work in ${prefix || "English"}`, async ({
    page,
    request,
  }) => {
    const response = await page.goto(
      `${prefix}/learn/scientific-agents/agent-resource-guide/`,
    );
    expect(response?.status()).toBe(200);
    for (const path of artifacts) {
      const link = page.locator(`main a[href="/downloads/${path}"]`);
      await expect(link).toBeVisible();
      await expect(link).toHaveAttribute("download", "");
      const clickedDownload = page.waitForEvent("download");
      await link.click();
      const saved = await clickedDownload;
      expect(saved.suggestedFilename()).toBe(path.split("/").at(-1));
      expect(await saved.failure()).toBeNull();
      const download = await request.get(`/downloads/${path}`);
      expect(download.status()).toBe(200);
      expect(await download.text()).toBe(await readFile(path, "utf8"));
    }
    expect(
      await page.evaluate(
        () => document.documentElement.scrollWidth <= innerWidth + 1,
      ),
    ).toBe(true);
  });
}
