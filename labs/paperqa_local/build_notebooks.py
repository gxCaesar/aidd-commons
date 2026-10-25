"""Build standalone bilingual notebooks from the curated PaperQA teaching example."""

# Multilingual prose and embedded observed text retain their original formatting.
# ruff: noqa: E501

import copy
import json
from inspect import getsource
from pathlib import Path
from textwrap import dedent

import nbformat
import run_smoke
from check_local_profile import router, validate_profile

ROOT = Path(__file__).parent


def verify_source_copies(example):
    """Check copied text and citation resolution, not semantic entailment."""
    documents = {doc["id"]: doc["text"] for doc in example["documents"]}
    checked = 0
    for answer in example["answers"]:
        for context in answer["contexts"]:
            text = documents.get(context["document_id"], "")
            if not context["source_text"] or context["source_text"] not in text:
                raise ValueError("Source text is not present in the named supplied document")
            if context["cited"] and context["chunk_name"] not in answer["references"]:
                raise ValueError("Cited chunk is missing from the answer references")
            checked += 1
    return {"answers": len(example["answers"]), "source_chunks_checked": checked}


def runtime_budget(profile):
    """Return transport limits only; scientific settings never depend on this."""
    budgets = {
        # Limits of the observed five-question batch, run on one GPU machine.
        "as-observed": {
            "num_thread": None,
            "chat_timeout": None,
            "embedding_timeout": None,
            "max_retries": None,
            "document_timeout": 150,
            "question_timeout": 600,
        },
        # Budget of the single accepted CPU execution copy of 10 September 2026,
        # which finished in 774.12 seconds on that machine, 708.61 of them in
        # the query. It is one machine's observation, not a validated default.
        "cpu-extended": {
            "num_thread": 4,
            "chat_timeout": 900,
            "embedding_timeout": 600,
            "max_retries": 0,
            "document_timeout": 600,
            "question_timeout": 2400,
        },
    }
    if profile not in budgets:
        raise ValueError("Unknown execution profile: " + str(profile))
    return budgets[profile]


def scientific_settings(value):
    """Drop transport limits; what remains must be identical across profiles."""
    transport = {"num_thread", "timeout", "max_retries", "num_retries", "kwargs", "router_kwargs"}
    if isinstance(value, dict):
        return {k: scientific_settings(v) for k, v in value.items() if k not in transport}
    if isinstance(value, list):
        return [scientific_settings(item) for item in value]
    return value


def apply_runtime_budget(effective, budget):
    """Apply thread and timeout limits, then prove no scientific field moved."""
    updated = copy.deepcopy(effective)
    if budget["num_thread"] is not None:
        for section, key in [
            (updated, "llm"),
            (updated, "summary_llm"),
            (updated["agent"], "agent_llm"),
            (updated["parsing"], "enrichment_llm"),
        ]:
            section[key + "_config"]["model_list"][0]["litellm_params"].update(
                num_thread=budget["num_thread"],
                timeout=budget["chat_timeout"],
                max_retries=budget["max_retries"],
            )
        embedding = updated["embedding_config"]
        embedding["model_list"][0]["litellm_params"]["num_thread"] = budget["num_thread"]
        embedding["kwargs"] = {
            "timeout": budget["embedding_timeout"],
            "num_retries": budget["max_retries"],
        }
        embedding["router_kwargs"] = {
            "timeout": budget["embedding_timeout"],
            "num_retries": budget["max_retries"],
        }
    if scientific_settings(updated) != scientific_settings(effective):
        raise ValueError("A runtime profile must not change model, retrieval or answer settings")
    return updated


def save_student_execution(folder, stage, answers, events, error=None):
    """Preserve student outputs on normal stages and caught failures."""
    (folder / "student_local_answers.json").write_text(
        json.dumps(answers, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (folder / "student_network_events.json").write_text(
        json.dumps(events, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (folder / "student_execution.json").write_text(
        json.dumps(
            {
                "stage": stage,
                "outcome": "failed" if error is not None else "stage_finished",
                "saved_answers": len(answers),
                "error": None if error is None else f"{type(error).__name__}: {error}",
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )


def definitions(*functions):
    return "\n\n".join(getsource(function).strip() for function in functions)


def build(language):
    example = json.loads((ROOT / "reviewed-example.json").read_text(encoding="utf-8"))
    verify_source_copies(example)
    cells = []

    def section(key, english, chinese, code=None, tags=()):
        cells.append(
            nbformat.v4.new_markdown_cell(
                dedent(chinese if language == "zh" else english).strip(), id=f"{key}-text"
            )
        )
        if code is not None:
            cells.append(
                nbformat.v4.new_code_cell(
                    dedent(code).strip(), id=f"{key}-code", metadata={"tags": list(tags)}
                )
            )

    section(
        "welcome",
        """
        # Local PaperQA: an answer is not the same as supported evidence

        **Question.** How do supplied documents become retrieved chunks, summaries
        and a cited answer, and which claims can we actually check?

        **Objectives.** Inspect original evidence separately from a model summary;
        recognize an unsupported extension of a correct answer; distinguish a
        refusal from proof that information is absent. Basic Python and the idea
        of retrieval-augmented generation are the prerequisites.

        This notebook defaults to **reading observed results**, with an editable
        evidence-check exercise. Download it and use Jupyter, or upload it through
        [Colab](https://colab.research.google.com/)'s **File → Upload notebook**.
        Default cells need only Python's standard library and Jupyter display:
        no package install, network request, API key, GPU or model call. The two
        attributed texts and all five actual answers are embedded in this file.

        An optional final section exposes local indexing and answering in separate
        editable cells. It needs separately prepared software and a local model
        server. It is not automatically enabled, including in Colab.
        """,
        """
        # 本地 PaperQA：有答案不等于有证据支持

        **问题。** 提供的文档如何变成检索片段、摘要与带引用的答案？哪些主张可以实际核对？

        **学习目标。** 将原文证据与模型摘要分开检查；识别正确答案中的无依据扩写；区分拒答与
        “信息不存在”的证明。需要基础 Python，以及检索增强生成的基本概念。

        本 notebook 默认**读取真实运行结果**，并提供可编辑的证据检查练习。下载后可用 Jupyter，
        或通过 [Colab](https://colab.research.google.com/) 的 **File → Upload notebook** 上传。
        默认 cell 仅需 Python 标准库与 Jupyter 显示功能，不安装软件包、不发网络请求、不需要
        API key、GPU 或模型调用。两篇附有许可和引用信息的文本及五条真实答案已嵌入文件。

        最后的可选部分将本地索引和问答拆成独立可编辑 cell，需要另外准备软件和本地模型服务。
        它不会自动开启，在 Colab 中也一样。
        """,
    )

    section(
        "setup",
        """
        ## 1. Choose the mode and create a student output folder

        Leave `ENABLE_LOCAL_INFERENCE = False` for the offline lesson. Output goes
        into a fresh folder; it does not overwrite the observed author answers.
        Editing a cell does not update a variable until you execute that cell.

        `EXECUTION_PROFILE` is read only by the optional local-inference section.
        A profile sets thread counts and time limits. It never changes the model,
        the questions, retrieval or generation settings, and section 9 refuses any
        profile that would move one of those fields. Keep `as-observed` until you
        have read the optional section; `cpu-extended` is described there.
        """,
        """
        ## 1. 选择模式并创建学生输出目录

        离线学习时保持 `ENABLE_LOCAL_INFERENCE = False`。输出写入新目录，不覆盖作者运行得到的
        答案。修改 cell 并不会更新变量，必须执行该 cell 才会生效。

        `EXECUTION_PROFILE` 只被可选的本地推理部分读取。配置只设置线程数与时间上限，不改变
        模型、问题、检索或生成设置；第 9 节会拒绝任何会改动这些字段的配置。阅读可选部分之前
        请保持 `as-observed`，`cpu-extended` 的含义在那里说明。
        """,
        """
        import asyncio
        import copy
        import importlib.metadata
        import json
        import os
        import sys
        import tempfile
        from pathlib import Path

        from IPython.display import display

        ENABLE_LOCAL_INFERENCE = False
        EXECUTION_PROFILE = "as-observed"
        OUTPUT_DIR = Path(tempfile.mkdtemp(prefix="paperqa-student-", dir=Path.cwd()))
        live_answers = []
        print("Student output:", OUTPUT_DIR)
        print("Execution profile:", EXECUTION_PROFILE, "(limits apply only to live inference)")
        """,
    )
    marker = "from IPython.display import display\n"
    head, tail = cells[-1].source.split(marker, 1)
    cells[-1].source = head + marker + "\n\n" + definitions(runtime_budget) + "\n\n" + tail
    cells[-1].source += "\n\n\n" + definitions(save_student_execution)

    section(
        "saved-example",
        """
        ## 2. Load the observed example

        The following data cell contains the unedited answer strings, retrieved
        contexts, source articles, settings and source-review notes. It is not a
        freshly generated model response. Expand the cell to inspect the payload.
        Question reference answers are teaching aids and are never passed to the
        model in the optional inference cells.
        """,
        """
        ## 2. 载入真实示例

        下方数据 cell 包含未改写的答案、检索片段、来源文章、设置与来源复核说明，不是新生成的
        模型回答。可展开 cell 查看完整数据。问题的参考答案只用于教学，不会传入后面的可选模型调用。
        """,
        "observed = json.loads(" + repr(json.dumps(example, ensure_ascii=False)) + ")",
        tags=("saved-example",),
    )
    cells[-1].metadata["jupyter"] = {"source_hidden": True}

    section(
        "documents",
        """
        ## 3. Inspect the source objects before the answers

        The object is a supplied article, not a discovered paper. Plain-text
        abstract/body sections were extracted from Europe PMC XML; references,
        figures and complete tables are not the input here. Open Babel (2011) is
        CC BY 2.0; CMMS-GCL (2023) is CC BY 4.0. Each text retains its title,
        authors, DOI and licence. This conversion is not a PDF-reading test.

        The library chunks these texts, embeds candidate chunks with a 768-dimensional
        local embedding model, retrieves evidence, summarizes it and generates an
        answer. The fixed setting retrieves four chunks and permits at most three
        answer sources. **Chunks are not independent papers or independent samples.**
        The printed documents and first question are the complete starting example.
        """,
        """
        ## 3. 先检查来源对象，再看答案

        对象是已提供的文章，不是智能体新发现的论文。输入从 Europe PMC XML 提取摘要和正文纯文本，
        不包括参考文献、图像和完整表格。Open Babel（2011）采用 CC BY 2.0，CMMS-GCL（2023）采用
        CC BY 4.0。每份文本保留题名、作者、DOI 与许可。这不是 PDF 阅读能力测试。

        库将文本切块，用 768 维本地嵌入模型表示候选片段，检索证据、生成摘要，再回答问题。
        固定设置检索四个片段，答案最多引用三个来源。**片段不等于独立论文，也不等于独立样本。**
        下方输出两份文档与第一个问题，构成完整起始示例。
        """,
        """
        for document in observed["documents"]:
            print(document["title"])
            print(document["citation"])
            print(document["url"], document["license_url"])
            print(document["text"][:700], "\\n")
        print(observed["questions"][0]["question"])
        """,
    )

    section(
        "copy-check",
        """
        ## 4. Check source copies and citation resolution

        This function checks whether every saved chunk occurs in its named input
        article and whether cited chunks appear in the reference list. It does
        **not** prove that the answer follows from that chunk. Copy fidelity and
        semantic support are different checks; the next section demonstrates why.
        """,
        """
        ## 4. 检查来源复制与引用对应

        该函数检查每个保存片段是否确实出现在对应输入文章中，以及被引用片段是否出现在引用列表。
        它**不能**证明答案可由该片段推出。复制一致性与语义支持是两种不同的检查，下一节会展示区别。
        """,
        definitions(verify_source_copies)
        + "\n\ncopy_check = verify_source_copies(observed)\nprint(copy_check)",
    )

    section(
        "inspect-answer",
        """
        ## 5. Read an answer, its model summary and the original passage

        Change `question_index` from 0 through 4 and rerun this cell. Index 0's
        opening claim, over 110 formats, is directly supported by the Open Babel
        abstract. Do not use the model's summary as a substitute for the source.
        The whole answer is displayed; correct opening sentences do not excuse
        unsupported sentences later in the response.
        """,
        """
        ## 5. 对照答案、模型摘要和原文

        将 `question_index` 改为 0 到 4，再执行本 cell。第 0 题开头的“超过 110 种格式”直接受到
        Open Babel 摘要支持。不要用模型摘要替代原文。下方显示完整答案；开头正确不代表后面的扩写都正确。
        """,
        """
        question_index = 0
        selected = observed["answers"][question_index]
        print("QUESTION:", selected["question"])
        print("ANSWER:", selected["answer"])
        print("REFERENCES:", selected["references"])
        for context in selected["contexts"]:
            if context["cited"]:
                print("\\nCITED CHUNK:", context["chunk_name"])
                print("MODEL SUMMARY:", context["summary"])
                print("ORIGINAL TEXT:", context["source_text"])
        """,
    )

    section(
        "review",
        """
        ## 6. Preserve the observed weakness

        All four answerable questions have supported core answers. But question 2
        names fingerprint and fastsearch, then loosely assigns molecular-summary
        generation to them. The original text assigns that function to the **report
        format**. This extra-prose error is retained in the saved answer.

        The CMMS-GCL answer's extra “best performance” statement refers to results
        reported in that paper's protocols and comparisons, not a new reproduction
        or a general ranking. The negative-control question elicited a refusal;
        its sole returned context is one Open Babel chunk. That is appropriate
        restraint, not proof of absence across both papers or all literature.

        These notes are source-grounded assistant review, not human grading or a
        benchmark score. Five questions from two known public papers cannot measure
        generalization, calibration or the causal benefit of retrieval; pretraining
        exposure is possible. No setting was retuned after observing these answers.
        """,
        """
        ## 6. 保留实际出现的不足

        四个可回答问题的核心答案都有原文支持。但第 2 题先给出 fingerprint 与 fastsearch，随后
        笼统地把生成分子摘要的功能也归给它们。原文把该功能归于 **report format**。保存的答案保留了
        这个扩写错误，没有为了显得正确而改写。

        CMMS-GCL 答案扩写中的“best performance”指该论文在其协议和比较范围内报告的结果，不是
        本教程的新复现或通用排名。负控题得到了拒答，但实际只返回一个 Open Babel 片段。这体现了
        合适的克制，不证明两篇全文或整个文献中都不存在相关信息。

        这些说明来自助手对来源的复核，不是人类评分或基准分数。两篇公开论文上的五个问题不能衡量
        泛化、校准或检索的因果收益；模型可能在预训练时见过文章。本次没有观察答案后再调整设置。
        """,
        """
        for row, review in zip(observed["answers"], observed["source_review"], strict=True):
            print(row["id"], "—", review["verdict"])
            print("Returned documents:", sorted({c["document_id"] for c in row["contexts"]}))
            print(review["limitation"], "\\n")
        print("Observed runtime (not an accuracy table):", observed["observations"])
        """,
    )

    section(
        "exercise",
        """
        ## 7. Independent evidence exercise

        Without generating a new answer, identify the utility format that produces
        a molecular-structure summary. Write your answer and a supporting sentence
        in the two strings below, then inspect the worked answer. Explain why this
        corrects the second saved response without changing its core search-format
        answer. There is no automatic reasoning grade.

        <details><summary>Worked answer</summary>
        The report format produces a molecular-structure summary. Fingerprint and
        fastsearch are the two search utility formats. One paragraph discusses all
        three, so a citation to that paragraph can still accompany a wrong mapping.
        </details>
        """,
        """
        ## 7. 独立证据练习

        不生成新答案，指出哪个 utility format 生成分子结构摘要。在下方两个字符串填写答案与支持句，
        再查看参考解释。说明为什么这能纠正第 2 个保存答案，又不改变其核心搜索格式答案。本练习不自动
        评分推理质量。

        <details><summary>参考解释</summary>
        report format 生成分子结构摘要；fingerprint 和 fastsearch 是两个搜索 utility formats。
        同一段落讨论了三者，所以即使引用该段，具体的功能对应也可能错误。
        </details>
        """,
        """
        student_answer = ""
        student_supporting_sentence = ""
        document = next(d for d in observed["documents"] if d["id"] == "openbabel-2011")
        support_is_verbatim = bool(student_supporting_sentence) and student_supporting_sentence in document["text"]
        print("A supplied supporting sentence appears verbatim:", support_is_verbatim)
        print("This literal check does not grade the explanation.")
        """,
    )

    section(
        "known-bad",
        """
        ## 8. Prove the narrow source checker can fail

        Alter a **copy** of a real retrieved chunk. The checker must reject the
        invented text; the original saved example stays unchanged. This proves
        only the copy check, not that it detects every unsupported answer.
        """,
        """
        ## 8. 证明这个有限的来源检查能发现错误

        修改真实检索片段的**副本**。检查器必须拒绝虚构文本，原始示例保持不变。这只验证复制检查，
        不能说明它能发现所有无依据答案。
        """,
        """
        altered = copy.deepcopy(observed)
        altered["answers"][0]["contexts"][0]["source_text"] = "An invented sentence outside the supplied articles."
        invented_chunk_rejected = False
        try:
            verify_source_copies(altered)
        except ValueError as error:
            invented_chunk_rejected = True
            print("Expected rejection:", error)
        assert invented_chunk_rejected
        """,
    )

    section(
        "local-prerequisites",
        """
        ## Optional: fresh local inference, not the default lesson

        Use a separately prepared Linux/Jupyter environment with Python 3.11+,
        `paper-qa[pypdf]==2026.8.12`, Ollama 0.33.3, `qwen3:8b` and
        `nomic-embed-text:v1.5`. The observed integration used Python 3.13.13 and
        an RTX A6000. Its sampled GPU peak was 7.334 GB; this is not a minimum
        requirement or a promise on another machine. Budget memory and obtain
        permission before using shared compute. The model downloads total about
        5.5 GB, excluding runtime software. No hosted API fallback is configured.

        Prepare packages, model weights and tokenizer assets **before** enabling
        the local cells. These setup commands use the internet and do not run in
        the notebook automatically. Use an isolated environment, not a system one:

        ```sh
        python -m pip install 'paper-qa[pypdf]==2026.8.12'
        OLLAMA_NO_CLOUD=1 OLLAMA_HOST=127.0.0.1:11434 OLLAMA_CONTEXT_LENGTH=8192 OLLAMA_NUM_PARALLEL=1 ollama serve
        # In another terminal, once this server is ready:
        ollama pull qwen3:8b
        ollama pull nomic-embed-text:v1.5
        python -c 'import tiktoken; [tiktoken.get_encoding(n) for n in ("cl100k_base", "o200k_base")]'
        ```

        Do not start a duplicate server or stop one you do not own. Official
        [Ollama setup](https://docs.ollama.com/quickstart) and
        [cloud-disable settings](https://docs.ollama.com/faq) explain the server.
        The notebook does not install Ollama, change credentials, select a GPU,
        start a server, download weights or recover failed downloads for you.

        Only then set `ENABLE_LOCAL_INFERENCE = True` and rerun the mode cell
        and subsequent cells. The following source-visible SDK steps mirror the
        tested integration.

        Set `EXECUTION_PROFILE` in that same cell. A profile changes limits only:

        | Limit | `as-observed` | `cpu-extended` |
        | --- | --- | --- |
        | Model threads per request | server default | 4 |
        | SDK retries | library default | 0 |
        | Chat call limit | library default | 900 s |
        | Embedding config limit | library default | 600 s |
        | Per-document limit | 150 s | 600 s |
        | Per-question limit | 600 s | 2400 s |

        `as-observed` keeps the limits of the observed five-question batch, which
        ran with a GPU. The first CPU-only attempt used them, stopped at the
        150-second limit while embedding the first document and produced no
        answer. Its log shows 20 compute threads confined to four logical CPUs,
        which supports thread oversubscription as a contributor, not as a proven
        sole cause.

        `cpu-extended` reproduces the runtime budget of the one accepted CPU
        execution copy. That copy completed all 12 code cells in **774.12 seconds**
        on one machine, about **708.61 seconds** of it inside the query, which is
        longer than the `as-observed` 600-second question limit. Its single new
        answer states a supported core fact, then overstates a conversion test and
        adds reliability guarantees the paper does not make. The original five
        saved answers are unchanged.

        Selecting the profile copies that budget, not that outcome. Your machine,
        core count and memory differ; the copy moved threads and time limits
        together, so it isolates neither; and in that run the embedding timeout
        was not forwarded into the HTTP call, leaving the per-document limit as
        the real outer bound. Neither profile is a validated default CPU recipe,
        and no profile changes a scientific setting. Both offline editions have
        executed.
        """,
        """
        ## 可选：新的本地推理，不是默认练习

        使用单独准备的 Linux/Jupyter 环境，包含 Python 3.11+、`paper-qa[pypdf]==2026.8.12`、
        Ollama 0.33.3、`qwen3:8b` 和 `nomic-embed-text:v1.5`。真实集成运行采用 Python 3.13.13
        与 RTX A6000，采样显存峰值为 7.334 GB；它不是最低要求，也不保证其他机器的表现。使用共享
        算力前先估算资源并取得许可。模型下载合计约 5.5 GB，不含运行软件；没有托管 API 回退。

        开启本地 cell **之前**，先准备软件包、模型和 tokenizer 资源。下面的安装命令需要网络，
        不会在 notebook 中自动执行。请使用隔离环境，不要直接安装到系统环境：

        ```sh
        python -m pip install 'paper-qa[pypdf]==2026.8.12'
        OLLAMA_NO_CLOUD=1 OLLAMA_HOST=127.0.0.1:11434 OLLAMA_CONTEXT_LENGTH=8192 OLLAMA_NUM_PARALLEL=1 ollama serve
        # 在另一个终端中，等待服务就绪后：
        ollama pull qwen3:8b
        ollama pull nomic-embed-text:v1.5
        python -c 'import tiktoken; [tiktoken.get_encoding(n) for n in ("cl100k_base", "o200k_base")]'
        ```

        不要启动重复服务或停止不属于自己的服务。可参考 [Ollama 安装说明](https://docs.ollama.com/quickstart)
        与[云功能关闭说明](https://docs.ollama.com/faq)。本 notebook 不会代你安装 Ollama、修改凭据、
        选择 GPU、启动服务、下载权重或恢复失败的下载。

        准备好后，再将 `ENABLE_LOCAL_INFERENCE = True`，重新执行模式 cell 及后续 cell。
        下方显式 SDK 步骤沿用已运行集成的调用方式。

        在同一个 cell 中设置 `EXECUTION_PROFILE`。配置只改变各项上限：

        | 上限 | `as-observed` | `cpu-extended` |
        | --- | --- | --- |
        | 每次请求的模型线程数 | 服务默认 | 4 |
        | SDK 重试次数 | 库默认 | 0 |
        | 单次聊天调用时限 | 库默认 | 900 秒 |
        | 嵌入配置时限 | 库默认 | 600 秒 |
        | 单篇文档时限 | 150 秒 | 600 秒 |
        | 单个问题时限 | 600 秒 | 2400 秒 |

        `as-observed` 保持已观测的五问题批次所用上限，那次运行使用 GPU。首次 CPU-only 尝试沿用
        这组上限，在为首篇文档做 embedding 时于 150 秒处停止，没有产生答案。其日志显示 20 个计算
        线程被限制在四个逻辑 CPU 上，这支持线程超额分配是一个促成因素，但没有证明它是唯一原因。

        `cpu-extended` 复现唯一一次通过验收的 CPU 执行副本的运行时预算。该副本在一台机器上于
        **774.12 秒**内完成全部 12 个代码 cell，其中约 **708.61 秒**发生在问答阶段，已超过
        `as-observed` 的 600 秒问题时限。它产生的那一条新答案核心事实有支持，但随后扩大了转换
        测试的结论，并加入原文没有给出的可靠性保证。原有五条答案保持不变。

        选择该配置复制的是那份预算，不是那次结果：你的机器、核数与内存并不相同；该副本同时改动
        线程与时限，因此无法区分两者各自的作用；而且在那次运行中嵌入超时并未传递到 HTTP 调用，
        真正的外层约束是单篇文档时限。两个配置都不是经过验证的默认 CPU 配方，任何配置都不改动
        科学设置。双语离线版均已执行。
        """,
    )

    section(
        "local-settings",
        """
        ## 9. Inspect and configure every local model role

        The visible helpers below check the narrow base profile and apply the
        observed chat transport/settings. Both indexing and answering receive
        the same settings and embedding object; no default hosted model is used.
        The runtime profile is applied last, after the assertion that the settings
        still equal the observed ones. `apply_runtime_budget` then compares both
        versions with transport limits removed and raises if any other field
        differs, so a profile cannot quietly change a model, retrieval or answer
        setting. A Python socket guard permits only the loopback Ollama port. It is
        not an OS sandbox and cannot audit the separate server or native networking.
        The guard remains installed in this kernel: restart the kernel to remove
        it. Missing dependencies or a missing server are errors, not fallback cues.
        """,
        """
        ## 9. 检查并配置每一个本地模型角色

        下方可见辅助函数检查有限的基础配置，并应用真实运行使用的聊天接口和设置。索引与问答都
        显式接收相同的设置和嵌入对象，不使用默认托管模型。运行时配置在最后一步应用，即在断言
        设置仍等于已观测设置之后；`apply_runtime_budget` 会去掉传输类上限后比较两份设置，只要
        还有其他字段不同就抛错，因此配置无法悄悄改动模型、检索或回答设置。Python socket 检查
        仅允许本机 Ollama 端口；它不是操作系统沙盒，不能审计单独运行的服务或原生库网络行为。
        检查钩子会保留在 kernel 中，需要重启 kernel 才能移除。依赖或服务缺失应报错，不触发
        其他服务回退。
        """,
        definitions(
            router,
            validate_profile,
            run_smoke.smoke_settings,
            scientific_settings,
            apply_runtime_budget,
            run_smoke.install_network_guard,
        )
        + "\n\n"
        + dedent("""
        if ENABLE_LOCAL_INFERENCE:
            local_network_events = []
            try:
                if importlib.metadata.version("paper-qa") != "2026.8.12":
                    raise RuntimeError("This lesson requires paper-qa 2026.8.12")
                effective = smoke_settings(copy.deepcopy(observed["base_profile"]))
                assert effective == observed["effective_settings"]
                effective = apply_runtime_budget(effective, runtime_budget(EXECUTION_PROFILE))
                os.environ.update(LITELLM_LOCAL_MODEL_COST_MAP="True", HF_HUB_OFFLINE="1",
                                  NO_PROXY="127.0.0.1,localhost,::1", no_proxy="127.0.0.1,localhost,::1")
                install_network_guard(local_network_events)
                from lmi import LiteLLMEmbeddingModel
                from paperqa import Docs, Settings
                settings = Settings(**effective)
                embedding = LiteLLMEmbeddingModel(name=settings.embedding, ndim=768, config=settings.embedding_config)
                llm, summary_llm = settings.get_llm(), settings.get_summary_llm()
                local_docs = Docs()
                print("Runtime limits:", runtime_budget(EXECUTION_PROFILE))
                print("Local objects constructed; no documents indexed yet.")
            except BaseException as error:
                save_student_execution(OUTPUT_DIR, "configure", live_answers, local_network_events, error)
                raise
            else:
                save_student_execution(OUTPUT_DIR, "configure", live_answers, local_network_events)
        else:
            print("Offline mode: no SDK import, server contact or model load.")
        """).strip(),
    )

    section(
        "local-index",
        """
        ## 10. Index the two supplied texts

        This is the explicit indexing step, not an opaque command-line runner.
        Text is written only in the new student folder. Accurate document metadata
        avoids external metadata lookup. Each call uses the selected profile's
        per-document limit: 150 seconds under `as-observed`, 600 under `cpu-extended`.
        """,
        """
        ## 10. 为两份文本建立索引

        这里显式展示索引步骤，而不是调用隐藏流程的命令行 runner。文本只写入新的学生目录。
        显式提供准确元数据，避免外部元数据查询。每次调用使用所选配置的单篇文档时限：
        `as-observed` 为 150 秒，`cpu-extended` 为 600 秒。
        """,
        """
        if ENABLE_LOCAL_INFERENCE:
            try:
                for document in observed["documents"]:
                    path = OUTPUT_DIR / (document["id"] + ".txt")
                    with path.open("x", encoding="utf-8") as stream:
                        stream.write(document["text"])
                    added = await asyncio.wait_for(local_docs.aadd(
                        path, citation=document["citation"], docname=document["id"],
                        dockey=document["id"], title=document["title"], settings=settings,
                        llm_model=llm, embedding_model=embedding,
                    ), timeout=runtime_budget(EXECUTION_PROFILE)["document_timeout"])
                    if added is None:
                        raise RuntimeError("Document was not indexed: " + document["id"])
                    print("Indexed:", document["id"])
            except BaseException as error:
                save_student_execution(OUTPUT_DIR, "index", live_answers, local_network_events, error)
                raise
            else:
                save_student_execution(OUTPUT_DIR, "index", live_answers, local_network_events)
        """,
    )

    section(
        "local-answer",
        """
        ## 11. Ask one question and inspect the returned evidence

        This cell passes only `local_question` as question text, never the reference
        answer, review verdict or saved model answer. It uses the selected profile's
        per-question limit: 600 seconds under `as-observed`, 2400 under `cpu-extended`.
        Editing it defines a fresh student query, not another author benchmark.
        Inspect the whole response and evidence even if the first sentence is right.
        New responses may differ from the saved ones despite temperature zero.
        """,
        """
        ## 11. 提问并检查返回证据

        本 cell 只把 `local_question` 作为问题传入，不发送参考答案、复核结论或保存的模型答案。
        使用所选配置的单个问题时限：`as-observed` 为 600 秒，`cpu-extended` 为 2400 秒。
        修改问题产生的是新的学生查询，不是另一次作者基准实验。即使第一句正确，
        也要检查完整回答及证据。温度为零仍不能保证新回答与保存答案完全相同。
        """,
        """
        local_question = observed["questions"][0]["question"]
        if ENABLE_LOCAL_INFERENCE:
            try:
                session = await asyncio.wait_for(local_docs.aquery(
                    local_question, settings=settings, llm_model=llm,
                    summary_llm_model=summary_llm, embedding_model=embedding,
                ), timeout=runtime_budget(EXECUTION_PROFILE)["question_timeout"])
                result = {
                    "question": local_question, "answer": session.answer,
                    "references": session.references,
                    "contexts": [{"document_id": c.text.doc.dockey,
                                  "chunk_name": c.text.name, "source_text": c.text.text,
                                  "summary": c.context} for c in session.contexts],
                }
                live_answers.append(result)
                print(result["answer"])
                print(result["references"])
                display(result["contexts"])
                if any(not event["allowed"] for event in local_network_events):
                    raise RuntimeError("External Python network attempt blocked; inspect student events")
            except BaseException as error:
                save_student_execution(OUTPUT_DIR, "answer", live_answers, local_network_events, error)
                raise
            else:
                save_student_execution(OUTPUT_DIR, "answer", live_answers, local_network_events)
        """,
    )

    section(
        "report",
        """
        ## 12. Keep the student report separate

        The report records which mode and runtime profile you used, the literal
        source-copy check and your exercise response. It does not turn the five examples into an accuracy
        score. Saved author answers remain untouched. Export this report yourself
        if you need a backup: saving the notebook does not back up its output folder.
        If a live cell failed, preserve its partial files and error rather than
        repeatedly querying until a preferred answer appears.

        **Sources.** [Open Babel](https://doi.org/10.1186/1758-2946-3-33),
        [CMMS-GCL](https://doi.org/10.1093/bioinformatics/btad503),
        [PaperQA's pinned Docs interface](https://github.com/Future-House/paper-qa/blob/v2026.08.12/src/paperqa/docs.py).
        Third-party article text retains the licences printed above; original
        lesson prose is CC BY 4.0 and original lesson code is Apache-2.0.
        """,
        """
        ## 12. 单独保存学生报告

        报告记录运行模式与运行时配置、字面来源检查和练习回答，不把五个示例转换成准确率。作者的原始答案保持
        不变。如需备份，请自行导出报告：保存 notebook 不等于备份输出目录。实时 cell 若失败，
        应保留已有文件和错误，不要反复提问直到得到偏好的答案。

        **来源。** [Open Babel](https://doi.org/10.1186/1758-2946-3-33)、
        [CMMS-GCL](https://doi.org/10.1093/bioinformatics/btad503)、
        [PaperQA 固定版本的 Docs 接口](https://github.com/Future-House/paper-qa/blob/v2026.08.12/src/paperqa/docs.py)。
        第三方文章文本保留前述许可；原创教程文字采用 CC BY 4.0，原创教程代码采用 Apache-2.0。
        """,
        """
        student_report = {
            "mode": "fresh_local_query" if ENABLE_LOCAL_INFERENCE else "read_saved_answers",
            "execution_profile": EXECUTION_PROFILE,
            "runtime_budget": runtime_budget(EXECUTION_PROFILE),
            "saved_answer_count": len(observed["answers"]),
            "source_copy_check": "passed",
            "invented_chunk_rejected": invented_chunk_rejected,
            "new_inference_performed": bool(live_answers),
            "exercise_answer": student_answer,
            "exercise_supporting_sentence": student_supporting_sentence,
            "support_is_verbatim": support_is_verbatim,
            "limitation": "Copy checks do not establish semantic support; no benchmark score is computed.",
        }
        path = OUTPUT_DIR / "student_report.json"
        path.write_text(json.dumps(student_report, ensure_ascii=False, indent=2) + "\\n", encoding="utf-8")
        print(path)
        display(student_report)
        """,
    )

    return nbformat.v4.new_notebook(
        cells=cells,
        metadata={
            "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
            "language_info": {"name": "python", "version": "3.11"},
        },
    )


if __name__ == "__main__":
    for language, suffix in (("en", ""), ("zh", ".zh-CN")):
        notebook = build(language)
        nbformat.validate(notebook)
        nbformat.write(notebook, ROOT / f"paperqa_local_tutorial{suffix}.ipynb")
