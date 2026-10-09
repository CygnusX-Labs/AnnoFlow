# =============================================================================
# AnnoFlow - 08. 交付（Flow framework §6.4 通用接口）
# =============================================================================
# 输入复用 snakefile 层算好的 DELIVER_INPUTS（§5.6-2 禁止二次调用目标生成）。
# 默认 copy 模式；禁止默认 symlink（§6.4，symlink 悬空风险已验证）。
# 目标列表经 {input:q} 加引号传参（§6.4）。
# =============================================================================

rule delivery:
    """
    交付分析结果到 data_deliver 目录。

    Outputs:
        {data_deliver}/delivery_manifest.json  交付文件清单（来源、大小、MD5、动作）
        {data_deliver}/delivery_manifest.md5   各交付文件 MD5 列表
        {data_deliver}/delivery_details.log    逐文件交付日志
    """
    input:
        DELIVER_INPUTS,
    output:
        manifest_json=os.path.join(config["data_deliver"], "delivery_manifest.json"),
        manifest_md5=os.path.join(config["data_deliver"], "delivery_manifest.md5"),
        manifest_log=os.path.join(config["data_deliver"], "delivery_details.log"),
    params:
        source_dir=config["workflow"],
        target_dir=config["data_deliver"],
        pipeline=config["pipeline_version"],
        project=config["project_name"],
    conda:
        workflow.source_path("../env/py3.12.yaml")
    resources:
        **rule_resource(config, 'default', skip_queue_on_local=True, logger=logger)
    log:
        "logs/08.deliver/delivery.log"
    benchmark:
        "benchmarks/08.deliver/delivery.txt"
    message:
        "📤 Delivering results to {params.target_dir}"
    shell:
        """
        python3 "{DELIVER_SCRIPT}" \
            --inputs {input:q} \
            --source-dir "{params.source_dir}" \
            --target-dir "{params.target_dir}" \
            --pipeline "{params.pipeline}" \
            --project "{params.project}" \
            > {log} 2>&1
        """
