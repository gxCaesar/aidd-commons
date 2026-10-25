import { describe, expect, it } from "vitest";

import { colabNotebookUrl } from "../../site/src/lib/notebook-launch.js";

describe("versioned student notebook launches", () => {
  it("pins both language editions in each standalone exercise to a source commit", () => {
    const revision = "49b692b969958b40a7c7461a7b8e245ef0f58bc1";
    const pairs = [
      ["molecule_representations", "representation_inspector"],
      ["student_modelling", "student_modelling_tutorial"],
      ["lipophilicity", "lipophilicity_tutorial"],
      ["paperqa_local", "paperqa_local_tutorial"],
    ];
    for (const [directory, stem] of pairs) {
      for (const language of ["", ".zh-CN"]) {
        const path = `labs/${directory}/${stem}${language}.ipynb`;
        const url = new URL(colabNotebookUrl(path, revision)!);
        expect(url.origin).toBe("https://colab.research.google.com");
        expect(url.pathname).toBe(
          `/github/gxCaesar/aidd-commons/blob/${revision}/${path}`,
        );
      }
    }
  });

  it("supports a release tag without launching a frozen result notebook", () => {
    expect(
      colabNotebookUrl(
        "labs/paperqa_local/paperqa_local_tutorial.ipynb",
        "v0.2.1",
      ),
    ).toContain("/blob/v0.2.1/");
    expect(
      colabNotebookUrl(
        "labs/freesolv/freesolv_honest_baselines.ipynb",
        "v0.2.1",
      ),
    ).toBeUndefined();
    expect(
      colabNotebookUrl("labs/lipophilicity/README.md", "v0.2.1"),
    ).toBeUndefined();
  });

  it("rejects a moving branch or invalid source revision", () => {
    const path = "labs/lipophilicity/lipophilicity_tutorial.ipynb";
    for (const revision of ["main", "", "../../main"]) {
      expect(() => colabNotebookUrl(path, revision)).toThrow(
        "published commit",
      );
    }
  });
});
