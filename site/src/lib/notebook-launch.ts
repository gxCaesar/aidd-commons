/** Only editable student notebooks have a hosted launch route. */
export function colabNotebookUrl(
  path: string,
  revision: string,
): string | undefined {
  if (
    !/^labs\/(?:molecule_representations|student_modelling|lipophilicity|paperqa_local)\/[^/]+\.ipynb$/u.test(
      path,
    )
  ) {
    return undefined;
  }
  if (!/^(?:[a-f\d]{40}|v\d+\.\d+\.\d+(?:-[\w.-]+)?)$/u.test(revision)) {
    throw new Error(
      "Notebook launches require a published commit or version tag.",
    );
  }
  return `https://colab.research.google.com/github/gxCaesar/aidd-commons/blob/${revision}/${path}`;
}
