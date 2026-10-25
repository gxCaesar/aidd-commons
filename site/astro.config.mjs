import { defineConfig } from "astro/config";
import starlight from "@astrojs/starlight";

export default defineConfig({
  site: process.env.AIDD_SITE_URL,
  base: process.env.AIDD_BASE_PATH || "/",
  integrations: [
    starlight({
      title: "AIDD Commons",
      description:
        "An open learning and reference system for AI drug discovery.",
      customCss: ["./src/styles/global.css"],
      locales: {
        root: { label: "English", lang: "en" },
        "zh-cn": { label: "简体中文", lang: "zh-CN" },
      },
      routeMiddleware: "./src/route-middleware.ts",
      components: {
        Pagination: "./src/components/LessonPagination.astro",
      },
      sidebar: [
        {
          label: "AIDD Commons",
          items: [
            {
              label: "Learn",
              link: "/learn/foundations/getting-started/",
              translations: { "zh-CN": "学习" },
            },
            {
              label: "Atlas",
              link: "/atlas/",
              translations: { "zh-CN": "图谱（英文）" },
            },
            {
              label: "Labs",
              link: "/labs/",
              translations: { "zh-CN": "实验室" },
            },
            {
              label: "Audit",
              link: "/audit/",
              translations: { "zh-CN": "审计（英文）" },
            },
            {
              label: "Report",
              link: "/report/",
              translations: { "zh-CN": "报告（英文）" },
            },
            {
              label: "Contribute",
              link: "/contribute/",
              translations: { "zh-CN": "参与（英文）" },
            },
          ],
        },
      ],
    }),
  ],
});
