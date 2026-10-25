# ruff: noqa: E501

from __future__ import annotations

from pathlib import Path
from textwrap import dedent

import nbformat

LAB_DIRECTORY = Path(__file__).resolve().parent
REPOSITORY_ROOT = LAB_DIRECTORY.parents[1]
CANONICAL_CORE_PATH = (
    REPOSITORY_ROOT / "labs" / "src" / "aidd_commons" / "representations" / "inspection.py"
)
NOTEBOOK_PATHS = (
    LAB_DIRECTORY / "representation_inspector.ipynb",
    LAB_DIRECTORY / "representation_inspector.zh-CN.ipynb",
)


def _code_cells(canonical_core: str) -> list[str]:
    return [
        dedent(
            """
            import importlib.metadata
            import subprocess
            import sys

            REQUIRED_PYTHON = (3, 11)
            REQUIRED_RDKIT = "2025.9.6"


            def normalized_version(value):
                return tuple(int(part) for part in value.split("."))

            if sys.version_info < REQUIRED_PYTHON:
                raise RuntimeError(
                    f"Python {REQUIRED_PYTHON[0]}.{REQUIRED_PYTHON[1]} or newer is required; "
                    f"this runtime is {sys.version.split()[0]}."
                )

            try:
                installed_rdkit = importlib.metadata.version("rdkit")
            except importlib.metadata.PackageNotFoundError:
                installed_rdkit = None

            loaded_rdkit = sys.modules.get("rdkit")
            if loaded_rdkit is not None and normalized_version(
                getattr(loaded_rdkit, "__version__", "0")
            ) != normalized_version(REQUIRED_RDKIT):
                raise RuntimeError(
                    "A different RDKit version is already loaded. Restart the runtime, then rerun "
                    "this setup cell so it can install the pinned version safely."
                )

            if installed_rdkit is None or normalized_version(installed_rdkit) != normalized_version(
                REQUIRED_RDKIT
            ):
                subprocess.check_call(
                    [sys.executable, "-m", "pip", "install", f"rdkit=={REQUIRED_RDKIT}"]
                )
                raise RuntimeError(
                    "RDKit was installed or changed. Restart the runtime, then rerun this notebook "
                    "from the first cell."
                )

            import rdkit

            if normalized_version(rdkit.__version__) != normalized_version(REQUIRED_RDKIT):
                raise RuntimeError(
                    f"Loaded RDKit {rdkit.__version__}, expected {REQUIRED_RDKIT}. Restart the runtime."
                )

            print(f"Python {sys.version.split()[0]}; RDKit {rdkit.__version__}")
            """
        ).strip(),
        canonical_core.rstrip(),
        dedent(
            """
            EXAMPLES = (
                MoleculeInput(
                    "pyridine-kekule",
                    "C1=CC=CN=C1",
                    "Equivalent graph written with explicit alternating bonds",
                ),
                MoleculeInput(
                    "pyridine-aromatic",
                    "n1ccccc1",
                    "Equivalent graph written with aromatic atoms",
                ),
                MoleculeInput(
                    "alanine-one",
                    "N[C@@H](C)C(=O)O",
                    "One defined tetrahedral stereoisomer",
                ),
                MoleculeInput(
                    "alanine-two",
                    "N[C@H](C)C(=O)O",
                    "The opposite defined tetrahedral stereoisomer",
                ),
                MoleculeInput(
                    "alanine-unspecified",
                    "NC(C)C(=O)O",
                    "Connectivity retained but tetrahedral stereochemistry unspecified",
                ),
                MoleculeInput("acetic-acid", "CC(=O)O", "Neutral protonation state"),
                MoleculeInput(
                    "sodium-acetate",
                    "CC(=O)[O-].[Na+]",
                    "Disconnected salt with two components",
                ),
            )
            CONFIG = RepresentationConfig(
                morgan_radius=2,
                morgan_bits=2048,
                include_chirality=True,
            )
            report = build_report(EXAMPLES, config=CONFIG)
            report_payload = json.loads(render_report(report))

            assert len(report.molecules) == len(EXAMPLES)
            assert report.contract.morgan_radius == 2
            assert report.contract.morgan_bits == 2048
            assert report.contract.include_chirality is True
            print(f"Inspected {len(report.molecules)} label-free examples.")
            """
        ).strip(),
        dedent(
            """
            from html import escape

            from IPython.display import HTML, SVG, display
            from rdkit import Chem
            from rdkit.Chem.Draw import rdMolDraw2D


            def html_table(headers, rows):
                header_html = "".join(f"<th>{escape(str(header))}</th>" for header in headers)
                row_html = "".join(
                    "<tr>" + "".join(f"<td>{escape(str(value))}</td>" for value in row) + "</tr>"
                    for row in rows
                )
                return (
                    "<table><thead><tr>"
                    + header_html
                    + "</tr></thead><tbody>"
                    + row_html
                    + "</tbody></table>"
                )


            def molecule_svg(smiles, legend):
                molecule = Chem.MolFromSmiles(smiles)
                if molecule is None:
                    raise RepresentationInputError(f"could not draw invalid SMILES: {smiles}")
                drawer = rdMolDraw2D.MolDraw2DSVG(300, 220)
                rdMolDraw2D.PrepareAndDrawMolecule(drawer, molecule, legend=legend)
                drawer.FinishDrawing()
                return drawer.GetDrawingText()


            by_id = {item.source_id: item for item in report.molecules}
            display(
                HTML(
                    html_table(
                        ("example", "input", "canonical isomeric SMILES", "formula", "components"),
                        [
                            (
                                item.source_id,
                                item.input_smiles,
                                item.canonical_isomeric_smiles,
                                item.molecular_formula,
                                item.component_count,
                            )
                            for item in report.molecules
                        ],
                    )
                )
            )

            display(
                HTML(
                    html_table(
                        ("pyridine input", "canonical isomeric SMILES", "InChIKey"),
                        [
                            (item.input_smiles, item.canonical_isomeric_smiles, item.inchi_key)
                            for item in (
                                by_id["pyridine-kekule"],
                                by_id["pyridine-aromatic"],
                            )
                        ],
                    )
                )
            )
            display(
                HTML(
                    html_table(
                        (
                            "alanine example",
                            "isomeric SMILES",
                            "non-isomeric SMILES",
                            "specified / unassigned stereocenters",
                        ),
                        [
                            (
                                item.source_id,
                                item.canonical_isomeric_smiles,
                                item.canonical_nonisomeric_smiles,
                                f"{item.specified_stereocenters} / {item.unassigned_stereocenters}",
                            )
                            for item in (
                                by_id["alanine-one"],
                                by_id["alanine-two"],
                                by_id["alanine-unspecified"],
                            )
                        ],
                    )
                )
            )
            sodium_acetate = by_id["sodium-acetate"]
            display(
                HTML(
                    html_table(
                        ("salt", "canonical isomeric SMILES", "components", "formal charge"),
                        [
                            (
                                sodium_acetate.source_id,
                                sodium_acetate.canonical_isomeric_smiles,
                                sodium_acetate.component_count,
                                sodium_acetate.formal_charge,
                            )
                        ],
                    )
                )
            )

            for item in report.molecules:
                display(HTML(f"<h4>{escape(item.source_id)}</h4>"))
                display(SVG(molecule_svg(item.input_smiles, item.source_id)))
            """
        ).strip(),
        dedent(
            """
            import tempfile
            from pathlib import Path

            from IPython.display import FileLink, display

            output_directory = Path(
                tempfile.mkdtemp(prefix="aidd-representation-inspector-", dir=Path.cwd())
            )
            report_path = output_directory / "representation-report.json"
            with report_path.open("x", encoding="utf-8") as report_file:
                report_file.write(render_report(report))
            report_json = report_path.read_text(encoding="utf-8")

            print(f"REPORT_PATH={report_path}")
            print("Wrote a fresh JSON report and retained it for download.")
            display(FileLink(str(report_path), result_html_prefix="Download: "))

            print(
                "REPORT_JSON="
                + json.dumps(
                    json.loads(report_json),
                    ensure_ascii=False,
                    separators=(",", ":"),
                    sort_keys=True,
                )
            )
            """
        ).strip(),
    ]


def _english_markdown() -> list[str]:
    return [
        """# Label-free small-molecule representation inspector

**Mode:** editable student exercise. This notebook uses seven authored teaching examples embedded below. It does not download data, load activity labels, fit a model, make a split, or report predictive performance.

For Colab, download this `.ipynb` file and choose **File > Upload notebook**. Local Jupyter is an alternative. The setup cell requires Python 3.11 or newer and uses RDKit 2025.9.6. It installs that exact package only when missing or mismatched; if it changes RDKit, restart the runtime before rerunning the notebook. No GPU is needed. This notebook has not been verified in Colab.

It creates `representation-report.json` in a fresh directory beneath the notebook's current working directory and retains it for download. It never reads or changes author results, caches, or local project files. Delete the generated directory yourself when it is no longer needed. Resetting the runtime clears variables; rerun cells in order.""",
        """## Question and computational objects

A SMILES string is an input notation, not an experimental measurement. RDKit parses that notation into a molecular graph, then derives canonical isomeric and non-isomeric SMILES, an InChIKey, simple 2D descriptors, a Murcko scaffold, and two hashed Morgan fingerprint summaries. The code reports a binary fingerprint's occupied bit count and a count fingerprint's nonzero-feature count. Neither number is a biological or physicochemical target.

The next code cell embeds the repository's tested inspection dataclasses and functions verbatim. Keeping them inside the notebook makes the uploaded file self-contained while preserving the canonical radius 2, 2,048-bit, chirality-aware Morgan configuration.""",
        """## Seven authored examples

The pair of pyridine strings should canonicalize to the same RDKit identity. The two defined alanines should keep distinct isomeric representations while sharing a non-isomeric one. The unspecified alanine is not assigned to either enantiomer. Sodium acetate remains a two-component record; the notebook neither chooses a parent fragment nor neutralizes it.""",
        """## Inspect, compare, and draw

The tables compare graph-derived fields. The SVG drawings make the input graph visible; they do not establish a solution conformation, binding pose, affinity, efficacy, safety, or synthesizability. Canonicalization also does not decide protonation, tautomer state, or assay identity.""",
        """## Fresh output

The output cell creates a fresh retained directory beneath its current working directory, exclusively creates `representation-report.json`, prints its path, and displays a download link. Delete that generated directory yourself when it is no longer needed; do not point this exercise at a frozen author-results directory.""",
        """## Exercises and answers

1. Before looking at the tables, predict whether the two pyridine inputs will have the same canonical isomeric SMILES and InChIKey. **Answer:** yes in this RDKit version; they encode the same parsed graph.
2. Which alanine field loses the distinction between the two defined enantiomers? **Answer:** canonical non-isomeric SMILES; the isomeric strings and InChIKeys remain different.
3. Does a net-zero sodium acetate record become one neutral molecule here? **Answer:** no. It remains two components, even though the summed formal charge is zero.
4. Add one valid SMILES with a new source ID to `EXAMPLES`. Predict which reported fields can change. Then replace it with `not-a-smiles`. **Answer:** a valid molecule adds one additional inspected record; the malformed input raises `RepresentationInputError` rather than being silently excluded.

This is a representation exercise, not a QSAR, endpoint, training, or evaluation protocol.""",
    ]


def _chinese_markdown() -> list[str]:
    return [
        """# 无标签小分子表示检查器

**模式：** 可编辑的学生练习。本 notebook 使用下方内嵌的七个作者编写教学示例。它不下载数据、不加载活性标签、不拟合模型、不定义数据划分，也不报告预测性能。

在 Colab 中，请下载此 `.ipynb` 文件，然后选择 **File > Upload notebook**。本地 Jupyter 也是替代方案。设置单元要求 Python 3.11 或更新版本，并使用 RDKit 2025.9.6。只有在缺失或版本不匹配时才安装该确切版本；若改变了 RDKit，重启 runtime 后再从头运行。本练习不需要 GPU。本 notebook 尚未在 Colab 中验证。

它会在 notebook 当前工作目录下新建目录并写入 `representation-report.json`，保留该文件供下载。它不会读取或改变作者结果、缓存或本地项目文件。不再需要时请自行删除生成的目录。重启 runtime 会清除变量；请按顺序重新运行各单元。""",
        """## 问题与计算对象

SMILES 字符串是输入记法，不是实验测量。RDKit 将该记法解析为分子图，然后导出 canonical isomeric 和 non-isomeric SMILES、InChIKey、简单 2D descriptors、Murcko scaffold 以及两种 hashed Morgan fingerprint 摘要。代码报告二进制 fingerprint 的 occupied bit 数和 count fingerprint 的 nonzero feature 数。这两个数都不是生物学或理化 target。

下一段代码逐字嵌入仓库中经过测试的 inspection dataclass 和 function。将其保留在 notebook 中，可使上传后的文件独立运行，同时保持 canonical 的 radius 2、2,048-bit、chirality-aware Morgan configuration。""",
        """## 七个作者编写的示例

两条 pyridine 字符串在 RDKit 中应 canonicalize 为相同身份。两个已定义的 alanine 应保留不同的 isomeric 表示，但共享 non-isomeric 表示。未指定立体化学的 alanine 不会被分配给任一对映体。sodium acetate 保持为两个 component；本 notebook 不选择 parent fragment，也不进行 neutralization。""",
        """## 检查、比较与绘图

表格比较由分子图导出的字段。SVG 图展示输入图，但不能建立溶液构象、结合 pose、affinity、efficacy、safety 或 synthesizability。canonicalization 同样不能决定 protonation、tautomer state 或 assay identity。""",
        """## 新鲜输出

输出单元会在当前工作目录下创建新的保留目录，以独占方式创建 `representation-report.json`，打印其路径并显示下载链接。不再需要时请自行删除该生成目录；不要把本练习指向冻结的作者结果目录。""",
        """## 练习与答案

1. 在查看表格前，预测两条 pyridine 输入是否会有相同的 canonical isomeric SMILES 和 InChIKey。**答案：** 在此 RDKit 版本中会相同；它们编码同一个已解析分子图。
2. 哪个 alanine 字段丢失了两个已定义对映体之间的区别？**答案：** canonical non-isomeric SMILES；isomeric string 和 InChIKey 仍然不同。
3. 净电荷为零的 sodium acetate 在这里会变成一个中性分子吗？**答案：** 不会。即使 formal charge 总和为零，它仍是两个 component。
4. 在 `EXAMPLES` 中加入一个具有新 source ID 的有效 SMILES。预测哪些报告字段会改变。然后将它替换为 `not-a-smiles`。**答案：** 有效分子会增加一条额外的已检查记录；格式错误的输入会抛出 `RepresentationInputError`，而不是被静默排除。

这是一个表示学习练习，不是 QSAR、endpoint、training 或 evaluation protocol。""",
    ]


def _notebook(markdown_cells: list[str], code_cells: list[str]) -> nbformat.NotebookNode:
    cells: list[nbformat.NotebookNode] = []
    for index, markdown in enumerate(markdown_cells):
        cells.append(nbformat.v4.new_markdown_cell(markdown))
        if index < len(code_cells):
            cells.append(nbformat.v4.new_code_cell(code_cells[index]))
    return nbformat.v4.new_notebook(
        cells=cells,
        metadata={
            "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
            "language_info": {"name": "python", "version": "3.11"},
        },
    )


def main() -> None:
    canonical_core = CANONICAL_CORE_PATH.read_text(encoding="utf-8")
    code_cells = _code_cells(canonical_core)
    for output_path, markdown_cells in zip(
        NOTEBOOK_PATHS,
        (_english_markdown(), _chinese_markdown()),
        strict=True,
    ):
        nbformat.write(_notebook(markdown_cells, code_cells), output_path)
        print(f"Wrote clean notebook: {output_path.relative_to(REPOSITORY_ROOT)}")


if __name__ == "__main__":
    main()
