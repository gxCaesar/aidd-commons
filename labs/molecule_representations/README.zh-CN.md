# 无标签小分子表示检查器

## 模式与边界

这是一个可编辑的学生练习，不是模型训练或 benchmark protocol。它内嵌七个作者编写的教学示例，不下载分子数据、不加载活性标签、不拟合模型、不定义数据划分，也不报告预测性能。它与已完成的 FreeSolv、ChEMBL、rMD17 和 pool-budget 结果分离。

本检查器比较由输入 SMILES 导出的计算对象：RDKit 分子图、canonical isomeric 和 non-isomeric SMILES、InChIKey、六个简单 2D descriptor、Murcko scaffold 与 hashed Morgan fingerprint 摘要。descriptor 或 fingerprint 不是实验性质。

## 以 notebook 为入口

使用英文版 [representation inspector](representation_inspector.ipynb) 或中文版 [representation inspector](representation_inspector.zh-CN.ipynb)。两个文件具有完全相同的可执行单元，且保存时不带输出。

在托管环境中，请下载其中一个 notebook，并在 Google Colab 选择 **File > Upload notebook**。不要 clone repository，也不要运行 helper CLI。本地 Jupyter 也是可用选择。第一个单元要求 Python 3.11 或更新版本，并检查 RDKit 2025.9.6。只有在该版本缺失或不匹配时才安装确切版本。若安装改变了 RDKit，请重启 runtime 后从第一个单元重新运行。本 notebook 尚未在 Colab 中验证。

仓库测试会在隔离的本地 `nbclient` kernel 中执行两个 notebook 版本：将保留的七条记录 JSON 报告与 canonical `build_report` 输出比对，断言实际 SVG 与 HTML 表格输出，检查加入一个有效示例后得到八条记录，并确认错误 SMILES 会 fail closed。这只是本地验证；Colab 仍未验证。

不需要 GPU。若已具有固定依赖，七个分子的练习通常只需很短的 CPU 时间。示例数据写在 notebook 内，因此不需要下载数据集或账户。

## 应检查什么

- Kekule 与 aromatic 两条 pyridine 字符串会解析为同一个 RDKit canonical isomeric SMILES 和 InChIKey。
- 两个已定义的 alanine 对映体保留不同的 isomeric SMILES 和 InChIKey，而 non-isomeric SMILES 会折叠这一差异。
- 未指定立体化学的 alanine 不会被静默分配为任一对映体。
- Sodium acetate 保持为两个 component。本练习不选择 parent fragment、不进行 neutralization，也不将它与 acetic acid 合并。
- SVG 绘图使已解析的分子图可见，但不能建立溶液构象、结合 pose、affinity、efficacy、safety 或 synthesizability。

Notebook 内嵌经过测试的 canonical inspection dataclass 与 function，保持 Morgan radius 2、2,048 bits 和 chirality enabled。它展示比较表、SVG 绘图、这些观察背后的机制，以及带答案的独立问题。诸如 `not-a-smiles` 的非法输入会可见地抛出 `RepresentationInputError`，不会被静默移除。

## 输出与重置边界

最后一个单元会在 notebook 当前工作目录下创建一个新目录，并以独占方式在其中创建 `representation-report.json`。它会打印精确路径并显示下载链接；不再需要时请自行删除该生成目录。它不会读取或改变作者缓存、结果目录或冻结 protocol artifact。重启 notebook runtime 会清除内存状态；重置后请按顺序重新运行各单元。

底层语法与实现可参考
[OpenSMILES specification source](https://github.com/opensmiles/OpenSMILES/blob/master/opensmiles.asciidoc)、
[IUPAC InChI project](https://iupac.org/who-we-are/divisions/division-details/inchi/)、
[RDKit Book](https://www.rdkit.org/docs/RDKit_Book.html) 与
[RDKit Python guide](https://www.rdkit.org/docs/GettingStartedInPython.html)。
