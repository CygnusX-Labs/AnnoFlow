# =============================================================================
# AnnoFlow - 07. AI 逐蛋白可靠性评估
# =============================================================================
# 由模块开关 ai（config.yaml）经 DataDeliver 目标生成驱动；
# AI 提供商设置读取 config["ai_config"]。
# =============================================================================

rule ai_annotation_curator:
    """
    使用 AI 对注释结果进行智能分析和解读。

    该规则会调用 AI 模型（默认本地 Ollama）对 eggnog 和 KofamScan
    的注释结果进行综合分析，生成质量评估和功能摘要。
    """
    input:
        eggnog = "01.eggnog/{sample}_eggnog.tsv",
        kofam = "02.kofam/{sample}_kofam.tsv"
    output:
        report = "04.ai/{sample}_ai_report.md",
        json = "04.ai/{sample}_ai_analysis.json",
        tsv = "04.ai/{sample}_ai_analysis.tsv",
        csv = "04.ai/{sample}_ai_analysis.csv"
    params:
        provider = lambda wc: config.get("ai_config", {}).get("provider", "ollama"),
        model = lambda wc: config.get("ai_config", {}).get("model", "llama3.2"),
        api_key = lambda wc: config.get("ai_config", {}).get("api_key", ""),
        api_base = lambda wc: config.get("ai_config", {}).get("api_base", ""),
        taxonomy = lambda wc: config.get("taxonomy") or config.get("ai_config", {}).get("taxonomy", "Unknown"),
        max_proteins = lambda wc: config.get("ai_config", {}).get("max_proteins", 50),
        no_auto_filter = lambda wc: "--no-auto-filter" if config.get("ai_config", {}).get("no_auto_filter", False) else "",
        ai_curator_script = AI_CURATOR
    conda:
        workflow.source_path("../env/openai.yaml")
    log:
        "logs/07.ai/{sample}_ai_curator.log"
    benchmark:
        "benchmarks/07.ai/{sample}_ai_curator.txt"
    message:
        "🤖 Running AI analysis on {wildcards.sample}"
    shell:
        """
        # 构建基础命令
        CMD="python3 {params.ai_curator_script} -e {input.eggnog} -k {input.kofam} -s {wildcards.sample} -o {output.report} --output-json {output.json} --output-tsv {output.tsv} --output-csv {output.csv} --provider {params.provider} --model {params.model} --taxonomy '{params.taxonomy}' --max-proteins {params.max_proteins} {params.no_auto_filter}"

        # 追加 API key 和 API base 参数
        if [ -n "{params.api_key}" ]; then
            CMD="$CMD --api-key '{params.api_key}'"
            if ! echo "{params.api_key}" | grep -qE '^[A-Z_]+$'; then
                export AI_API_KEY="{params.api_key}"
            fi
        fi
        if [ -n "{params.api_base}" ]; then
            CMD="$CMD --api-base '{params.api_base}'"
            if ! echo "{params.api_base}" | grep -qE '^[A-Z_]+$'; then
                export AI_API_BASE="{params.api_base}"
            fi
        fi

        # 执行命令
        eval $CMD > {log} 2>&1
        """


rule ai_multi_sample_summary:
    """
    多样本 AI 汇总（单样本时复制首样本报告）。
    """
    input:
        ai_reports = expand("04.ai/{sample}_ai_report.md", sample=SAMPLES),
        eggnog_merged = "03.merge/eggnog_all_samples.tsv" if len(SAMPLES) > 1 else [],
        kofam_merged = "03.merge/kofam_all_samples.tsv" if len(SAMPLES) > 1 else []
    output:
        summary = "04.ai/AI_MULTI_SAMPLE_SUMMARY.md"
    params:
        samples = " ".join(SAMPLES),
        n_samples = len(SAMPLES),
        first_sample = SAMPLES[0] if SAMPLES else "",
        first_report = f"04.ai/{SAMPLES[0]}_ai_report.md" if SAMPLES else "",
    conda:
        workflow.source_path("../env/openai.yaml")
    log:
        "logs/07.ai/ai_multi_sample_summary.log"
    benchmark:
        "benchmarks/07.ai/ai_multi_sample_summary.txt"
    message:
        "🤖 Generating multi-sample AI summary"
    shell:
        """
        if [ {params.n_samples} -eq 1 ]; then
            # 单样本，复制报告
            if [ -f "{params.first_report}" ]; then
                cp "{params.first_report}" "{output.summary}"
            else
                echo "# AI Analysis Summary\\n\\nSample: {params.first_sample}\\n" > "{output.summary}"
            fi
        else
            # 多样本，创建汇总
            cat > "{output.summary}" << 'EOF'
# AI Multi-Sample Summary

Samples analyzed: {params.n_samples}
Samples: {params.samples}

## Individual Reports

EOF
            for report in {input.ai_reports}; do
                echo "- $report" >> "{output.summary}"
            done
        fi
        """
