# =============================================================================
# AnnoFlow - 09. Report（Flow framework §6.5 最小实现）
# =============================================================================
# 报告 rule 依赖本流程真实分析产物（经 REPORT_INPUTS，§6.5 强制）；
# deliver/report 目标由 DataDeliver 进入 rule all（§5.6-3）。
# =============================================================================

rule generate_project_summary:
    """
    生成 project_summary.json：项目元数据、样本列表、模块启用状态、
    关键产物清单与运行时间（§6.5 最小实现）。
    """
    input:
        REPORT_INPUTS,
    output:
        summary="project_summary.json",
    params:
        project_name=config["project_name"],
        species=config["species"],
        pipeline_version=config["pipeline_version"],
        samples=" ".join(SAMPLES),
        n_samples=len(SAMPLES),
        modules={k: (config.get(k) is not False) for k in
                 ["eggnog", "kofamscan", "integrate", "merge", "ai", "deliver", "report"]},
    resources:
        **rule_resource(config, 'low_resource', skip_queue_on_local=True, logger=logger)
    log:
        "logs/09.Report/generate_project_summary.log"
    benchmark:
        "benchmarks/09.Report/generate_project_summary.txt"
    message:
        "📋 Generating project_summary.json"
    run:
        import datetime
        import json
        import os

        existing_inputs = sorted({p for p in input if os.path.exists(p)})

        summary = {
            "project_meta": {
                "project_name": params.project_name,
                "species": params.species,
                "pipeline_version": params.pipeline_version,
                "analysis_date": datetime.date.today().isoformat(),
            },
            "stats": {
                "total_samples": int(params.n_samples),
                "samples": params.samples.split(),
                "output_files": len(existing_inputs),
            },
            "modules": params.modules,
            "outputs": existing_inputs,
        }

        with open(output.summary, "w", encoding="utf-8") as f:
            json.dump(summary, f, indent=2, ensure_ascii=False)
