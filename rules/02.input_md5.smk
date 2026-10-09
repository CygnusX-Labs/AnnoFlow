# =============================================================================
# AnnoFlow - 02. 输入蛋白序列 MD5 校验门控（Flow framework §4 适配）
# =============================================================================
# 硬性门控：所有样本输入文件 MD5 校验通过（或无期望 MD5 时记录基线）后
# 才生成 01.qc/md5_check.tsv；该文件是下游所有直接消费输入序列的 rule 的
# 显式 input 依赖（§4.3-1）。
#
# 说明：Flow 通用层的 seq_preprocessor / json_md5_verifier 面向 FASTQ 命名
# 约定，不适用于蛋白序列输入；本流程按 §4.2 设计原则（多线程校验、审计追踪、
# 无厂商 MD5 时计算并记录基线、任一失败即非零退出）以 Python 实现等价门控。
# =============================================================================

rule input_md5_check:
    """
    校验所有样本输入蛋白序列的 MD5，生成门控文件 01.qc/md5_check.tsv。
    """
    input:
        seqs=get_all_input_files,
    output:
        check_report="01.qc/md5_check.tsv",
    params:
        samples=" ".join(SAMPLES),
        md5_file=get_expected_md5_file,
    conda:
        workflow.source_path("../env/py3.12.yaml")
    resources:
        **rule_resource(config, 'default', skip_queue_on_local=True, logger=logger)
    log:
        "logs/02.input_md5/input_md5_check.log"
    benchmark:
        "benchmarks/02.input_md5/input_md5_check.txt"
    message:
        "🔐 Checking input MD5 for {params.samples}"
    shell:
        """
        python3 "{CHECK_INPUT_MD5}" \
            --samples {params.samples} \
            --input-dir "{INPUT_DIR}" \
            --output {output.check_report} \
            --md5-file "{params.md5_file}" \
            > {log} 2>&1
        """
