"""Build two standalone teaching notebooks from the same tested function source."""

from inspect import getsource
from pathlib import Path
from textwrap import dedent

import nbformat
import tutorial
from inspect_data import inspect as inspect_csv

ROOT = Path(__file__).parent


def definitions(*functions):
    return "\n\n".join(getsource(function).strip() for function in functions)


def build(language):
    cells = []

    def section(key, english, chinese, code=None, tags=()):
        cells.append(
            nbformat.v4.new_markdown_cell(
                dedent(chinese if language == "zh" else english).strip(),
                id=f"{key}-text",
            )
        )
        if code is not None:
            cells.append(
                nbformat.v4.new_code_cell(
                    dedent(code).strip(),
                    id=f"{key}-code",
                    metadata={"tags": list(tags)},
                )
            )

    section(
        "welcome",
        r"""
        # Predict lipophilicity: a notebook you can inspect and change

        **Mode: editable student exercise on public data.** This notebook trains new
        models in your own runtime. It never reads or overwrites the author's frozen
        FreeSolv or ChEMBL EGFR results. No reference model scores are supplied yet.
        An executed copy is your exercise, not an independent benchmark or discovery.

        **Question:** can eight physical descriptors or a molecular fingerprint
        predict measured logD at pH 7.4 for molecules with unseen scaffolds?
        You will learn to inspect molecules, separate fitting from selection, compare
        three baselines, and explain errors without tuning on the test set.
        Prerequisites: basic Python, arrays, train/validation/test, and regression.

        **Colab:** download this `.ipynb`, open [Colab](https://colab.research.google.com/),
        sign in and choose **File → Upload notebook**. Save your own copy. Choose a
        CPU runtime; this exercise does not need a GPU or API key. Local Jupyter is
        equally supported. No Drive mount is required. Runtime files are temporary:
        download your results before disconnecting. Free compute is not guaranteed;
        see the [official FAQ](https://research.google.com/colaboratory/faq.html).

        Run cells in order. After reading test errors, changes belong in a new
        exploratory copy and cannot count as a fresh test of the original recipe.
        Small-fixture engineering execution and real-assay results are different.
    """,
        r"""
        # 预测亲脂性：可以逐步理解与修改的 notebook

        **模式：公开数据上的可编辑学生练习。** 本 notebook 在你自己的运行时训练新模型，
        不读取或覆盖作者冻结的 FreeSolv、ChEMBL EGFR 结果。目前没有提供参考模型分数。
        运行副本是你的练习，不是独立 benchmark 验证或药物发现。

        **问题：** 八个物理描述符或分子指纹，能否预测未见骨架分子在 pH 7.4 的实测 logD？
        你将学习检查分子、区分拟合与选参、比较三个基线，以及不重新调测试集的误差解释。
        先修知识：基础 Python、数组、训练/验证/测试划分与回归。

        **Colab：** 下载本 `.ipynb`，打开 [Colab](https://colab.research.google.com/)，登录后选择
        **File → Upload notebook**，保存自己的副本。选择 CPU 运行时；无需 GPU 或 API key。
        也可使用本地 Jupyter。不要求挂载 Drive。运行时文件是临时的，断开前请下载结果。
        免费算力不保证持续可用，见 [官方 FAQ](https://research.google.com/colaboratory/faq.html)。

        按顺序执行。查看测试误差之后的修改应放入新的探索副本，不能算作对原 recipe 的新测试。
        小样本工程执行与真实测定结果是两回事。
    """,
    )
    section(
        "setup",
        """
        ## 1. Prepare only the libraries we need

        This cell installs missing or mismatched pinned dependencies into your
        current Python environment. In Colab that is your disposable runtime;
        for local Jupyter, first select a dedicated project kernel. Python 3.11+
        is required; the local reference environment is Python 3.11.
        The cell checks imported versions as well as installed package metadata.
        If an older library is still in memory, restart the session as instructed
        and run from the top. Installation failures are not a reason to silently
        change versions. Actual Colab execution has not yet been verified.
    """,
        """
        ## 1. 只准备需要的依赖

        本 cell 在当前 Python 环境安装缺失或版本不匹配的固定依赖。在 Colab 中，这是你的临时
        运行时；本地 Jupyter 请先选择独立的项目内核。需要 Python 3.11+，本地参考环境为 3.11。
        本 cell 同时检查内存中的已导入版本与已安装软件包的元数据。
        如果旧版库仍留在内存中，请按提示重启 session，再从头执行。安装失败时不要静默更换版本。
        当前尚未在真实 Colab 运行时验证。
    """,
        """
        import subprocess
        import sys
        from importlib.metadata import PackageNotFoundError, version

        # This standalone notebook also runs outside the project's Python constraints.
        if sys.version_info < (3, 11):  # noqa: UP036
            raise RuntimeError("Use Python 3.11 or newer")
        required = {
            "numpy": "2.4.6", "pandas": "2.3.3", "rdkit": "2025.9.6",
            "scikit-learn": "1.9.0", "matplotlib": "3.11.1",
        }


        def version_key(value):
            return tuple(int(part) if part.isdigit() else part for part in str(value).split("."))


        missing = []
        loaded = False
        for package, wanted in required.items():
            module_name = "sklearn" if package == "scikit-learn" else package
            module = sys.modules.get(module_name)
            imported_version = getattr(module, "__version__", "unknown")
            if module is not None and version_key(imported_version) != version_key(wanted):
                raise RuntimeError(
                    f"{package} {imported_version} is already loaded; expected {wanted}. "
                    "Restart the session, then Run all."
                )
            try:
                mismatch = version(package) != wanted
            except PackageNotFoundError:
                mismatch = True
            if mismatch:
                missing.append(f"{package}=={wanted}")
                loaded |= module is not None
        if missing:
            subprocess.check_call([sys.executable, "-m", "pip", "install", *missing])
            if loaded:
                raise RuntimeError("Dependencies changed: restart the session, then Run all")
        print("Python", sys.version.split()[0])
        print({package: version(package) for package in required})
    """,
        tags=("setup",),
    )
    section(
        "imports",
        """
        ## 2. Choose your working files

        The default CSV is downloaded into the current runtime only when absent.
        An existing named CSV is reused and validated, never silently replaced.
        Each full execution creates a new output directory beneath the notebook's
        current working directory, where the notebook file browser can find it. Re-executing
        export cells updates files inside that directory. Download those outputs
        if you want to keep them; none is written into another lab's results.
    """,
        """
        ## 2. 选择工作文件

        默认 CSV 仅在不存在时下载到当前运行时。已有同名文件会复用并检查，不会静默替换。
        每次完整执行在 notebook 当前工作目录下创建新的输出目录，可在 notebook 文件浏览器中找到；
        重复执行导出 cell 会更新该目录内的文件。
        要保留结果请下载；不会向其他实验的结果目录写入。
    """,
        """
        import csv
        import json
        import math
        import tempfile
        import warnings
        from collections import Counter, defaultdict
        from pathlib import Path
        from urllib.request import urlopen

        import matplotlib.pyplot as plt
        import numpy as np
        import pandas as pd
        from IPython.display import display
        from rdkit import Chem, DataStructs, rdBase
        from rdkit.Chem import Descriptors, Draw, rdFingerprintGenerator
        from rdkit.Chem.Scaffolds import MurckoScaffold
        from sklearn.exceptions import ConvergenceWarning
        from sklearn.linear_model import Ridge
        from sklearn.pipeline import make_pipeline
        from sklearn.preprocessing import StandardScaler
    """,
    )
    section(
        "parameters",
        """
        For your own local data copy, edit `DATA_PATH`. Keep the exact source and
        structure/endpoint contract. `DATA_KIND` labels the exported report; it
        does not transform invented labels into measurements.
    """,
        """
        使用自己的本地副本时修改 `DATA_PATH`，但应保持来源、结构和终点契约。
        `DATA_KIND` 只是导出报告的标记，不能把编造标签变成实验测量。
    """,
        """
        DATA_PATH = Path("Lipophilicity.csv")
        DATA_KIND = "public-MoleculeNet-lipophilicity"
        DATA_URL = "https://deepchemdata.s3-us-west-1.amazonaws.com/datasets/Lipophilicity.csv"
        OUTPUT_DIR = Path(tempfile.mkdtemp(prefix="aidd-lipophilicity-", dir=Path.cwd()))
    """,
        tags=("parameters",),
    )
    section(
        "source",
        """
        ## 3. Inspect the endpoint before building a model

        Source: [AstraZeneca deposit](https://doi.org/10.6019/CHEMBL3301361),
        [assay CHEMBL3301363](https://www.ebi.ac.uk/chembl/api/data/assay/CHEMBL3301363.json),
        and the CSV distributed by the [DeepChem 2.8.0 loader](https://github.com/deepchem/deepchem/blob/2.8.0/deepchem/molnet/load_function/lipo_datasets.py).
        ChEMBL data are [CC BY-SA 3.0](https://ftp.ebi.ac.uk/pub/databases/chembl/ChEMBLdb/latest/LICENSE);
        attribute the deposit and curation. Data are downloaded, not bundled here.

        `exp` measures logD at pH 7.4, not logP, binding affinity, or solubility.
        The dated intake on 9 September 2026 contained 4,200 rows (0.283 MB), all
        parseable. The server reported a 10 July 2020 modification date; this URL
        is not immutable. Current ChEMBL records were not joined row by row to this
        historical CSV. Keep the original structure strings, including water
        fragments; no target clipping or error-based exclusions.

        **Pause:** what would go wrong if the target were interpreted as pChEMBL?
        The unit, physical meaning and useful comparisons would all change.
    """,
        """
        ## 3. 建模前先检查终点

        来源：[AstraZeneca 数据存档](https://doi.org/10.6019/CHEMBL3301361)、
        [CHEMBL3301363 测定](https://www.ebi.ac.uk/chembl/api/data/assay/CHEMBL3301363.json)，以及
        [DeepChem 2.8.0 loader](https://github.com/deepchem/deepchem/blob/2.8.0/deepchem/molnet/load_function/lipo_datasets.py)
        提供的 CSV。
        ChEMBL 数据采用 [CC BY-SA 3.0](https://ftp.ebi.ac.uk/pub/databases/chembl/ChEMBLdb/latest/LICENSE)，
        应注明原始存档与整理来源。本 notebook 下载数据，不附带数据副本。

        `exp` 是 pH 7.4 的 logD，不是 logP、结合亲和力或溶解度。
        2026 年 9 月 9 日检查的下载包含 4,200 行（0.283 MB），均可解析。
        服务器报告修改日期为 2020 年 7 月 10 日，但这个 URL 不是不可变版本。
        本轮未将当前 ChEMBL 与历史 CSV 逐条连接。保留原始结构（包括水片段），
        不裁剪标签，也不按误差删样本。

        **停下来想一想：** 把该标签解释为 pChEMBL 会怎样？它的单位、物理意义与可用比较都会改变。
    """,
        definitions(inspect_csv, tutorial.load_frame)
        + "\n\n"
        + dedent("""
        if not DATA_PATH.exists():
            with urlopen(DATA_URL, timeout=60) as response:
                raw_csv = response.read()
            with DATA_PATH.open("xb") as handle:
                handle.write(raw_csv)
        frame = load_frame(DATA_PATH)
        print("Input kind:", DATA_KIND)
        display(pd.Series(inspect(DATA_PATH), name="intake"))
        display(frame.head())
    """),
    )
    section(
        "molecules",
        """
        ## 4. Look at molecules, not only arrays

        Each drawing is one supplied molecular record. Disconnected fragments
        remain visible; no hidden salt stripping is performed. Multiple records
        can share chemistry, so row count is not experimental replication.
        Look for rings, heteroatoms and flexible linkers. Which might affect
        membrane partitioning, and which effects depend on pH?
    """,
        """
        ## 4. 看分子，不只看数组

        每幅图对应一个原始分子记录。断开的片段仍然保留，没有隐藏的去盐步骤。
        多个记录可以共享化学特征，行数不是独立实验重复数。
        观察环、杂原子与柔性连接部分：哪些可能影响膜分配，哪些作用依赖 pH？
    """,
        """
        display(Draw.MolsToGridImage(
            [Chem.MolFromSmiles(s) for s in frame.smiles.head(6)],
            legends=frame.CMPD_CHEMBLID.head(6).tolist(),
            molsPerRow=3, subImgSize=(240, 180), useSVG=True,
        ))
    """,
    )
    section(
        "split",
        """
        ## 5. Split by scaffold before fitting

        We follow [DeepChem 2.8.0 scaffold ordering](https://github.com/deepchem/deepchem/blob/2.8.0/deepchem/splits/splitters.py):
        larger groups first, then larger first-row index for ties. Requested
        train/validation/test fractions are 80/10/10. Empty scaffolds stay in one
        group. RDKit version and row order matter; this is not a random split.
        Group-preserving row fractions may differ from the requested fractions.

        Train learns coefficients and preprocessing. Validation chooses alpha.
        Test evaluates the selected recipe. The assertions check complete assignment
        and no ID, exact-structure or scaffold overlap. They do not prove independent
        experimental batches or dissimilarity under every molecular representation.
    """,
        """
        ## 5. 拟合前按骨架划分

        遵循 [DeepChem 2.8.0 的骨架排序](https://github.com/deepchem/deepchem/blob/2.8.0/deepchem/splits/splitters.py)：
        先分配较大的组，同大小时首行索引较大的组在前。请求训练/验证/测试比例为 80/10/10。
        空骨架保留在同一组。RDKit 版本与原始行序会影响结果；这不是随机划分。
        保持整组可能使实际行数比例偏离目标。

        训练集学习系数与预处理，验证集选择 alpha，测试集评估选定方案。
        检查确保每行恰好分配一次，并且 ID、相同结构、骨架不跨集合。
        这并不能证明实验批次独立，也不意味着所有分子表示下都不相似。
    """,
        definitions(tutorial.validate_split, tutorial.scaffold_split)
        + "\n\n"
        + dedent("""
        splits = scaffold_split(frame)
        train, validation, test = (splits[name] for name in ("train", "validation", "test"))
        counts = {name: len(indices) for name, indices in splits.items()}
        display(pd.DataFrame([
            {"split": name, "rows": len(indices),
             "scaffold_groups": frame.iloc[indices].scaffold.nunique()}
            for name, indices in splits.items()
        ]))
        membership = frame[["CMPD_CHEMBLID", "canonical", "scaffold"]].copy()
        membership["split"] = ""
        for name, indices in splits.items():
            membership.loc[indices, "split"] = name
        membership.to_csv(OUTPUT_DIR / "split-membership.csv", index=False)
    """),
    )
    section(
        "features",
        """
        ## 6. Two representations of the same molecules

        The eight descriptor columns are molecular weight, MolLogP, polar surface
        area, H-bond donors and acceptors, ring count, rotatable bonds and fraction
        of sp3 carbons. **MolLogP is a feature, not a measured logD prediction.**
        Morgan encodes radius-2 local neighbourhoods in 2,048 bits, without chirality.
        Collisions are possible and 2D fingerprints do not describe assay conditions.

        Features do not read labels. Computing a fixed per-molecule fingerprint
        before partitioning its matrix is different from fitting a scaler on all rows.
        The next step fits every scaler on training rows only.
    """,
        """
        ## 6. 同一批分子的两种表示

        八列描述符分别为分子量、MolLogP、极性表面积、氢键供体与受体数、环数、可旋转键数、
        sp3 碳比例。**MolLogP 是一个特征，不是实测 logD 预测值。**
        Morgan 用 2,048 个 bit 编码 radius-2 局部邻域，不含手性信息；可能发生位碰撞，
        2D 指纹也没有表达测定条件。

        特征构造不读取标签。先为每个分子计算固定指纹，再划分矩阵，不等于用全数据拟合缩放器。
        下一步所有缩放器只在训练行拟合。
    """,
        definitions(tutorial.molecular_features)
        + "\n\n"
        + dedent("""
        descriptors, morgan, fingerprints = molecular_features(frame.smiles)
        features = {"descriptors": descriptors, "morgan": morgan}
        print("Descriptor shape:", descriptors.shape, "Morgan shape:", morgan.shape)
        print("Dense feature storage (MB):", round((descriptors.nbytes + morgan.nbytes) / 1e6, 2))
        descriptor_names = ["MolWt", "MolLogP", "TPSA", "NumHDonors", "NumHAcceptors",
                            "RingCount", "NumRotatableBonds", "FractionCSP3"]
        display(pd.DataFrame(descriptors[train[:5]], columns=descriptor_names))
        plt.hist(frame.iloc[train].exp, bins=20, edgecolor="white")
        plt.xlabel("Training logD at pH 7.4")
        plt.ylabel("Training molecules")
        plt.title("Training distribution only; no test-driven tuning")
        plt.show()
    """),
        tags=("pretraining-end",),
    )
    section(
        "fit",
        r"""
        ## 7. Train and select without looking at test errors

        First fit a constant: the training-label mean. It asks whether using the
        molecular input adds value. Ridge minimizes squared training error plus
        alpha times the squared coefficient norm; the intercept is unpenalized.
        Larger alpha shrinks coefficients more. Validation RMSE selects among
        `[0.1, 1, 10, 100]`; exact ties select the larger alpha.

        Descriptor scaling centers and scales. Bit scaling uses training variances
        without centering. Thus this compares two complete recipes, not an isolated
        causal effect of representation. LSQR uses tolerance 1e-6 and at most 10,000
        iterations. Stop on convergence failure. Keep the selected training fit;
        do not refit on train plus validation. This cell performs eight small Ridge
        fits on CPU. No result is known until you run it.

        **Before running:** predict how a constant baseline might beat a model.
        More features can increase variance or extrapolation error.
    """,
        r"""
        ## 7. 训练与选参，不看测试误差

        先拟合一个常数：训练标签均值。它用于判断分子输入是否带来额外价值。
        Ridge 最小化训练平方误差加 alpha 乘以系数平方和；截距不受惩罚。
        alpha 越大，系数收缩越强。用验证 RMSE 从 `[0.1, 1, 10, 100]` 中选择，
        精确同分时取较大 alpha。

        描述符中心化并缩放；bit 只按训练方差缩放、不中心化。因此比较的是两套完整 recipe，
        不是表示的孤立因果作用。LSQR 容差为 1e-6，最多 10,000 次迭代；不收敛就停止。
        保留选中的训练集拟合结果，不合并训练与验证重训。本 cell 在 CPU 上进行八次小型 Ridge
        拟合。在实际运行之前不知道结果。

        **运行前先预测：** 常数为何可能胜过模型？更多特征也可能增加方差或外推误差。
    """,
        definitions(tutorial.score, tutorial.fit_candidates)
        + "\n\n"
        + dedent("""
        y_train = frame.iloc[train].exp.to_numpy()
        y_validation = frame.iloc[validation].exp.to_numpy()
        train_mean = float(y_train.mean())
        selected_models, validation_scores, selected_alpha = {}, {}, {}
        for name, matrix in features.items():
            model, table = fit_candidates(
                matrix[train], y_train, matrix[validation], y_validation,
                center=(name == "descriptors"),
            )
            selected_models[name] = model
            validation_scores[name] = table.to_dict(orient="records")
            selected_alpha[name] = float(model.named_steps["ridge"].alpha)
            display(table.assign(representation=name))
        print("Selected alpha:", selected_alpha)
        print("Constant validation scores:",
              score(y_validation, np.full(len(validation), train_mean)))
    """),
        tags=("training",),
    )
    section(
        "evaluate",
        r"""
        ## 8. Evaluate once, keeping every test molecule

        RMSE is the square root of average squared error; MAE is average absolute
        error. Both use logD units. RMSE weights large errors more strongly.
        For errors `[1, -2]`, MAE = 1.5 and RMSE = sqrt(2.5), about 1.581.
        All three methods below use the same test molecules. Do not remove a model
        because it is worse than the constant, or select a new alpha here.

        Each plotted point is one test molecule, not an independent assay repeat.
        The dashed diagonal is perfect agreement; the residual line is zero error.
        Plots show all held-out records without error bars or post-hoc filtering.
    """,
        r"""
        ## 8. 评估一次，保留所有测试分子

        RMSE 是平均平方误差的平方根，MAE 是平均绝对误差，单位均为 logD。
        RMSE 对大误差更敏感。例如误差 `[1, -2]` 的 MAE = 1.5，RMSE = sqrt(2.5)，约 1.581。
        以下三种方法使用完全相同的测试分子。不能因为模型劣于常数就删掉它，也不能在此重新选 alpha。

        图中每个点是一条测试分子记录，不是独立的测定重复。虚线对角线代表完美一致，残差图横线
        代表零误差。图中保留全部测试记录，不显示误差棒，也不按结果过滤。
    """,
        """
        y_test = frame.iloc[test].exp.to_numpy()
        predictions = {"train_mean": np.full(len(test), train_mean)}
        for name, model in selected_models.items():
            predictions[name] = model.predict(features[name][test])
        test_metrics = {name: score(y_test, pred) for name, pred in predictions.items()}
        display(pd.DataFrame(test_metrics).T.rename_axis("method"))
        fig, axes = plt.subplots(1, 2, figsize=(11, 4), constrained_layout=True)
        low = min(y_test.min(), *(values.min() for values in predictions.values()))
        high = max(y_test.max(), *(values.max() for values in predictions.values()))
        for name, values in predictions.items():
            axes[0].scatter(y_test, values, s=16, alpha=0.55, label=name)
            axes[1].scatter(y_test, values - y_test, s=16, alpha=0.55, label=name)
        axes[0].plot([low, high], [low, high], "k--", linewidth=1)
        axes[1].axhline(0, color="black", linestyle="--", linewidth=1)
        axes[0].set(xlabel="Measured logD", ylabel="Predicted logD")
        axes[1].set(xlabel="Measured logD", ylabel="Prediction minus measurement")
        axes[0].legend()
        fig.suptitle(f"All {len(test)} test molecules; fixed selected models")
        fig.savefig(OUTPUT_DIR / "prediction-errors.png", dpi=140)
        plt.show()
    """,
        tags=("evaluation",),
    )
    section(
        "uncertainty",
        """
        ## 9. Compare paired errors, not just the smallest number

        For each named pair, report RMSE(left) minus RMSE(right). Negative means
        lower error for the left method. Resample whole test-scaffold groups with
        replacement, preserving all their molecules and pairing predictions.
        Recompute molecule-weighted RMSE differences in 2,000 resamples with seed
        20260909. The 2.5th/97.5th percentiles form a conditional 95% bootstrap interval.

        These are fixed-model, fixed-test-population uncertainty summaries. They
        assume scaffold groups are exchangeable; they omit training-set variation,
        measurement uncertainty and cross-assay shift. Three intervals are shown,
        without multiple-comparison correction or significance claims. With fewer
        than two groups the interval is not estimable. A narrow interval is not
        evidence that this is a SOTA model or that the assay is unbiased.
    """,
        """
        ## 9. 比较配对误差，不只找最小数字

        每对方法报告 RMSE(左) 减 RMSE(右)，负值表示左侧误差更低。
        对测试骨架组有放回重采样，保留整组全部分子及成对预测。
        在 2,000 次重采样中重新计算按分子加权的 RMSE 差，随机种子为 20260909。
        第 2.5/97.5 百分位组成条件性的 95% bootstrap 区间。

        这是固定模型、固定测试总体下的不确定性描述，假设骨架组可交换。
        它没有覆盖训练集变化、测量误差或跨测定迁移。三组区间均展示，不做多重比较校正，
        也不据此宣称显著性。少于两个组时区间不可估。区间很窄不代表模型是 SOTA 或测定无偏。
    """,
        definitions(tutorial.paired_interval)
        + "\n\n"
        + dedent("""
        intervals = {}
        for left, right in [("descriptors", "train_mean"), ("morgan", "train_mean"),
                            ("descriptors", "morgan")]:
            intervals[f"{left}-minus-{right}"] = paired_interval(
                y_test, predictions[left], predictions[right], frame.iloc[test].scaffold,
            )
        display(pd.DataFrame(intervals).T)
    """),
    )
    section(
        "diagnose",
        """
        ## 10. Explain a failure without changing the test

        These diagnostics were named before training: endpoint records, disconnected
        components, scaffold-group size and nearest-training Morgan/Tanimoto similarity.
        The original intake had one value at −1.5 and four at 4.5. Missing relation
        qualifiers do not establish that those boundary measurements are uncensored.
        Similarity is descriptive; it is not another training feature in this recipe.

        Inspect the tables, including empty slices. A pattern suggests a hypothesis,
        not a correction to apply retroactively. Missing batch/replicate columns
        prevent attributing errors to assay noise alone.
    """,
        """
        ## 10. 解释失败，但不修改测试集

        这些检查在训练前已列出：范围端点、断开组分、骨架组大小、最近训练分子的 Morgan/Tanimoto
        相似度。原始检查有 1 个 −1.5 和 4 个 4.5；缺少测定限定符不能证明端点未截尾。
        相似度只用于描述，不是本 recipe 新增的训练特征。

        查看表格，包括空的切片。模式只能提出假设，不能据此回头修正本次测试。
        缺少批次与重复测量字段，也就不能把误差全归因于测定噪声。
    """,
        """
        error_table = frame.iloc[test][["CMPD_CHEMBLID", "smiles", "scaffold", "exp"]].copy()
        for name, values in predictions.items():
            error_table[name] = values
            error_table[f"{name}_absolute_error"] = np.abs(values - y_test)
        error_table["range_endpoint"] = error_table.exp.isin([-1.5, 4.5])
        error_table["multicomponent"] = [
            len(Chem.GetMolFrags(Chem.MolFromSmiles(s))) > 1 for s in error_table.smiles
        ]
        error_table["scaffold_size"] = error_table.groupby("scaffold").scaffold.transform("size")
        train_fingerprints = [fingerprints[i] for i in train]
        error_table["nearest_train_similarity"] = [
            max(DataStructs.BulkTanimotoSimilarity(fingerprints[i], train_fingerprints))
            for i in test
        ]
        display(error_table.head(10))
        display(error_table.groupby("range_endpoint").agg(
            molecules=("exp", "size"), descriptor_mae=("descriptors_absolute_error", "mean"),
            morgan_mae=("morgan_absolute_error", "mean"),
        ))
        display(error_table.loc[error_table.multicomponent])
        error_table.to_csv(OUTPUT_DIR / "test-predictions.csv", index=False)
    """,
    )
    section(
        "report",
        """
        ## 11. Save a report you can explain

        The files contain your actual metrics, paired intervals, selections, split
        membership and predictions. No pretrained weights are required. Download
        the output folder's files using Colab's Files sidebar, and save the notebook
        with your observations. Do not upload sensitive data or another person's files.

        Write five sentences: the question and endpoint; data and split counts;
        validation-selected recipes; test errors and conditional differences;
        one limitation and a new-data check that could change your conclusion.
        Copy numbers from your run, not an expected answer. Preserve negative results.
    """,
        """
        ## 11. 保存一份自己能解释的报告

        输出包含本次实际指标、配对区间、选择、划分与预测，不需要预训练权重。
        在 Colab 左侧 Files 中下载输出目录内文件，并保存含有自己观察记录的 notebook。
        不要上传敏感数据或他人的文件。

        用五句话写报告：问题与终点；数据和划分数量；验证集选定的 recipe；测试误差与条件性差值；
        一个限制及可能改变结论的新数据检查。数字来自自己的运行，而不是参考答案。保留负结果。
    """,
        """
        summary = {
            "data_kind": DATA_KIND,
            "endpoint": "logD at pH 7.4",
            "counts": counts,
            "selected_alpha": selected_alpha,
            "validation_scores": validation_scores,
            "test_metrics": test_metrics,
            "paired_scaffold_intervals": intervals,
            "excluded_rows": 0,
            "interpretation": ("Student exercise; conditional fixed-model intervals; "
                               "not a SOTA or cross-assay claim"),
        }
        (OUTPUT_DIR / "summary.json").write_text(json.dumps(summary, indent=2, allow_nan=False))
        print("Your outputs:", OUTPUT_DIR)
        print("Files:", sorted(path.name for path in OUTPUT_DIR.iterdir()))
    """,
    )
    section(
        "exercise",
        """
        ## 12. Independent practice and answer checks

        1. **Before opening the validation table**, predict which alpha should shrink
           coefficients most. Inspect the selected model's `ridge.coef_` and the
           training scaler's `mean_`. Explain why neither used test labels.
        2. Compute RMSE and MAE by hand for three rows of your exported predictions.
           Compare with `score` on those same three rows, not the full test metric.
        3. In a separate copy, change only held-out `exp` values after keeping the
           same membership. Features, selected alpha and predictions should remain
           unchanged; reported errors should change. This is an engineering check
           with artificial labels, not an improved empirical result.
        4. If Morgan loses to the constant, propose one validation-only investigation
           and one genuinely new measurement. Do not rerank recipes on this test.

        **Answer checks:** 100 is the strongest candidate penalty; the pipeline fits
        its scaler only inside `fit_candidates` using training rows. A label change
        cannot alter a structure-only fingerprint. An error pattern alone does not
        identify its cause. For stronger evidence, collect a new assay/batch or an
        independently designed evaluation, rather than repeatedly reading this test.
    """,
        """
        ## 12. 独立练习与答案检查

        1. **打开验证表之前**，预测哪个 alpha 收缩系数最强。查看选中模型的 `ridge.coef_`
           和训练缩放器的 `mean_`，解释它们为什么都没有使用测试标签。
        2. 从导出预测中选三行手算 RMSE、MAE，再与同三行的 `score` 比较，不要与全测试指标混淆。
        3. 在独立副本中保持划分，只改 held-out `exp`。特征、选中的 alpha 与预测应保持不变，
           误差应改变。这是人工标签的工程检查，不是更好的实测结果。
        4. 如果 Morgan 劣于常数，提出一个只用验证集的检查和一个真正的新测量，不在本测试上重新排序。

        **答案检查：** 100 是候选中最强的惩罚；pipeline 只在 `fit_candidates` 内用训练行拟合
        缩放器。改标签不应改变只依赖结构的指纹。误差模式本身不能识别原因。
        更强证据需要新测定、新批次或独立设计的评估，而不是反复查看同一测试集。
    """,
    )
    return nbformat.v4.new_notebook(
        cells=cells,
        metadata={
            "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
            "language_info": {"name": "python"},
            "colab": {"toc_visible": True},
        },
    )


if __name__ == "__main__":
    for language, suffix in [("en", ""), ("zh", ".zh-CN")]:
        destination = ROOT / f"lipophilicity_tutorial{suffix}.ipynb"
        nbformat.write(build(language), destination)
        print(destination.name)
