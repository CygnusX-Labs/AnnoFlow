# =============================================================================
# AnnoFlow - 06. 多样本合并与汇总
# =============================================================================

rule merge_eggnog_results:
    """
    Merge eggnog results from all samples.
    """
    input:
        expand("01.eggnog/{sample}_eggnog.tsv", sample=SAMPLES)
    output:
        all_samples = "03.merge/eggnog_all_samples.tsv",
        high_conf = "03.merge/eggnog_highconf.tsv",
        stats = "03.merge/eggnog_stats.txt"
    params:
        samples = " ".join(SAMPLES),
    conda:
        workflow.source_path("../env/py3.12.yaml")
    resources:
        **rule_resource(config, 'default', skip_queue_on_local=True, logger=logger)
    log:
        "logs/06.merge/merge_eggnog.log"
    benchmark:
        "benchmarks/06.merge/merge_eggnog.txt"
    message:
        "📦 Merging eggnog results | {params.samples}"
    shell:
        """
        mkdir -p 03.merge && \
        chmod +x "{MERGE_RESULTS}" && \
        python3 "{MERGE_RESULTS}" \
            --input-dir 01.eggnog \
            --samples {params.samples} \
            --tool eggnog \
            --output-all {output.all_samples} \
            --output-high {output.high_conf} \
            --output-stats {output.stats} \
            > {log} 2>&1
        """

rule merge_kofam_results:
    """
    Merge KofamScan results from all samples.
    """
    input:
        expand("02.kofam/{sample}_kofam.tsv", sample=SAMPLES)
    output:
        all_samples = "03.merge/kofam_all_samples.tsv",
        high_conf = "03.merge/kofam_highconf.tsv",
        stats = "03.merge/kofam_stats.txt"
    params:
        samples = " ".join(SAMPLES),
    conda:
        workflow.source_path("../env/py3.12.yaml")
    resources:
        **rule_resource(config, 'default', skip_queue_on_local=True, logger=logger)
    log:
        "logs/06.merge/merge_kofam.log"
    benchmark:
        "benchmarks/06.merge/merge_kofam.txt"
    message:
        "📦 Merging KofamScan results | {params.samples}"
    shell:
        """
        mkdir -p 03.merge && \
        chmod +x "{MERGE_RESULTS}" && \
        python3 "{MERGE_RESULTS}" \
            --input-dir 02.kofam \
            --samples {params.samples} \
            --tool kofam \
            --output-all {output.all_samples} \
            --output-high {output.high_conf} \
            --output-stats {output.stats} \
            > {log} 2>&1
        """

rule compare_kegg_annotations:
    """Compare per-protein KEGG KO assignments between both annotation tools."""
    input:
        eggnog = expand("01.eggnog/{sample}_eggnog.tsv", sample=SAMPLES),
        kofam = expand("02.kofam/{sample}_kofam.tsv", sample=SAMPLES),
        eggnog_high = expand("01.eggnog/{sample}_eggnog_highconf.tsv", sample=SAMPLES),
        kofam_high = expand("02.kofam/{sample}_kofam_highconf.tsv", sample=SAMPLES)
    output:
        comparison = "03.merge/kegg_consistency.tsv",
        stats = "03.merge/kegg_consistency_stats.txt"
    params:
        samples = " ".join(SAMPLES)
    conda:
        workflow.source_path("../env/py3.12.yaml")
    resources:
        **rule_resource(config, 'default', skip_queue_on_local=True, logger=logger)
    log:
        "logs/06.merge/compare_kegg.log"
    benchmark:
        "benchmarks/06.merge/compare_kegg.txt"
    shell:
        """
        mkdir -p 03.merge && \
        python3 "{COMPARE_KEGG}" \
            --input-dir . \
            --samples {params.samples} \
            --output {output.comparison} \
            --stats {output.stats} \
            > {log} 2>&1
        """

rule export_annotation_sets:
    """Export GO from raw eggNOG and shared KO from both processed tools."""
    input:
        eggnog_raw=expand("01.eggnog/{sample}.emapper.annotations", sample=SAMPLES),
        eggnog=expand("01.eggnog/{sample}_eggnog.tsv", sample=SAMPLES),
        eggnog_high=expand("01.eggnog/{sample}_eggnog_highconf.tsv", sample=SAMPLES),
        kofam=expand("02.kofam/{sample}_kofam.tsv", sample=SAMPLES),
        kofam_high=expand("02.kofam/{sample}_kofam_highconf.tsv", sample=SAMPLES)
    output:
        go="03.merge/go_annotations.tsv",
        go_high="03.merge/go_annotations_highconf.tsv",
        gene2go="03.merge/gene2go.tsv",
        gene2go_high="03.merge/gene2go_highconf.tsv",
        go_stats="03.merge/go_annotation_stats.txt",
        shared="03.merge/kegg_shared.tsv",
        shared_high="03.merge/kegg_shared_highconf.tsv",
        gene2ko="03.merge/gene2ko_shared.tsv",
        gene2ko_high="03.merge/gene2ko_shared_highconf.tsv",
        shared_stats="03.merge/kegg_shared_stats.txt"
    params:
        samples=" ".join(SAMPLES), evalue=EVALUE_THRESHOLD, bitscore=BITSCORE_THRESHOLD
    conda:
        workflow.source_path("../env/py3.12.yaml")
    resources:
        **rule_resource(config, 'low_resource', skip_queue_on_local=True, logger=logger)
    log:
        "logs/06.merge/export_annotation_sets.log"
    benchmark:
        "benchmarks/06.merge/export_annotation_sets.txt"
    shell:
        """
        mkdir -p 03.merge && python3 "{EXPORT_ANNOTATION_SETS}" \
            --input-dir . --samples {params.samples} --evalue {params.evalue} \
            --bitscore {params.bitscore} --output-dir 03.merge > {log} 2>&1
        """

rule merge_summary_report:
    """
    Generate comprehensive summary report.
    """
    input:
        eggnog_stats = "03.merge/eggnog_stats.txt",
        kofam_stats = "03.merge/kofam_stats.txt",
        kegg_consistency_stats = "03.merge/kegg_consistency_stats.txt",
        annotation_sets = "03.merge/go_annotation_stats.txt",
        shared_stats = "03.merge/kegg_shared_stats.txt"
    output:
        report = "03.merge/SUMMARY_REPORT.txt"
    params:
        samples = " ".join(SAMPLES)
    resources:
        **rule_resource(config, 'low_resource', skip_queue_on_local=True, logger=logger)
    log:
        "logs/06.merge/merge_summary.log"
    benchmark:
        "benchmarks/06.merge/merge_summary.txt"
    message:
        "📝 Generating summary report"
    shell:
        """
        cat > {output.report} << EOF
================================================================================
AnnoFlow - Summary Report
================================================================================
Date: $(date '+%Y-%m-%d %H:%M:%S')
Samples: {params.samples}
================================================================================

eggnog-mapper Statistics:
EOF

        cat {input.eggnog_stats} >> {output.report}

        echo "" >> {output.report}
        echo "KofamScan Statistics:" >> {output.report}
        cat {input.kofam_stats} >> {output.report}

        echo "" >> {output.report}
        echo "KEGG KO Consistency (eggNOG-mapper vs KofamScan):" >> {output.report}
        cat {input.kegg_consistency_stats} >> {output.report}

        echo "" >> {output.report}
        echo "Independent GO and shared KEGG KO exports:" >> {output.report}
        cat {input.annotation_sets} >> {output.report}
        cat {input.shared_stats} >> {output.report}

        cat >> {output.report} << 'EOF'

Annotation counting and selection standards:
1. Total means unique protein query IDs in the tool's processed table. It must not be calculated as With KEGG + With GO, because these are overlapping subsets.
2. eggNOG high-confidence records are rows classified as High (score >= 80), while also passing configured E-value, Bit-score, and optional required-annotation filters.
3. KofamScan high-confidence records are the best KO hit per protein that passes the KofamScan significance threshold and score requirement.
4. GO outputs are functional annotations, not GO enrichment. GO complete uses raw annotations irrespective of KEGG; GO high-confidence requires configured E-value and Bit-score plus High confidence without requiring KEGG.
5. KO一致 in kegg_consistency.tsv means nonempty KO intersection, NOT equality of entire KO sets. Use kegg_shared.tsv for the exact shared KO(s), not integrated_ko or pathway IDs.
6. Shared high-confidence requires the same KO in both tools' high-confidence tables. The classifications come from the upstream protein/best-hit rows, not independent per-KO experimental evidence.
EOF

        echo "" >> {output.report}
        echo "================================================================================" >> {output.report}
        echo "Output Files:" >> {output.report}
        echo "  - 03.merge/eggnog_all_samples.tsv" >> {output.report}
        echo "  - 03.merge/kofam_all_samples.tsv" >> {output.report}
        echo "  - 03.merge/kegg_consistency.tsv" >> {output.report}
        echo "  - 03.merge/kegg_consistency_stats.txt" >> {output.report}
        echo "  - 03.merge/go_annotations.tsv / go_annotations_highconf.tsv" >> {output.report}
        echo "  - 03.merge/gene2go.tsv / gene2go_highconf.tsv" >> {output.report}
        echo "  - 03.merge/kegg_shared.tsv / kegg_shared_highconf.tsv" >> {output.report}
        echo "  - 03.merge/gene2ko_shared.tsv / gene2ko_shared_highconf.tsv" >> {output.report}
        echo "================================================================================" >> {output.report}
        """

rule annotation_summary:
    """
    Generate annotation summary for a single sample.
    """
    input:
        eggnog_formatted = "01.eggnog/{sample}_eggnog.tsv",
        eggnog_high_conf = "01.eggnog/{sample}_eggnog_highconf.tsv",
        kofam_formatted = "02.kofam/{sample}_kofam.tsv",
        kofam_high_conf = "02.kofam/{sample}_kofam_highconf.tsv"
    output:
        summary = "03.merge/{sample}_summary.txt"
    resources:
        **rule_resource(config, 'low_resource', skip_queue_on_local=True, logger=logger)
    log:
        "logs/06.merge/{sample}_summary.log"
    benchmark:
        "benchmarks/06.merge/{sample}_summary.txt"
    message:
        "📝 Generating summary for {wildcards.sample}"
    shell:
        """
        exec > {log} 2>&1
        cat > {output.summary} << EOF
================================================================================
Sample: {wildcards.sample}
Date: $(date '+%Y-%m-%d %H:%M:%S')
================================================================================

【eggnog-mapper】
EOF

        total=$(tail -n +14 {input.eggnog_formatted} | grep -v '^#' | wc -l)
        high=$(tail -n +2 {input.eggnog_high_conf} | grep -v '^#' | wc -l)

        echo "  Total: $total" >> {output.summary}
        echo "  High confidence: $high" >> {output.summary}

        kofam_total=$(tail -n +2 {input.kofam_formatted} | grep -v '^#' | wc -l)
        kofam_high=$(tail -n +2 {input.kofam_high_conf} | grep -v '^#' | wc -l)

        echo "" >> {output.summary}
        echo "【KofamScan】" >> {output.summary}
        echo "  Total: $kofam_total" >> {output.summary}
        echo "  High confidence: $kofam_high" >> {output.summary}

        echo "" >> {output.summary}
        echo "================================================================================" >> {output.summary}
        """


rule export_rnaflow_annotation:
    """
    导出 RNAFlow 可直接消费的 GO & KEGG 注释表（query/gos/kegg_pathway 等列），
    并生成 ko##### 通路 ID -> 通路名映射（本地缓存优先，否则走 KEGG REST）。
    """
    input:
        eggnog = "03.merge/eggnog_all_samples.tsv"
    output:
        annotation = "03.merge/rnaflow_annotation.tsv",
        pathway_names = "03.merge/kegg_pathway_names.tsv"
    params:
        names_cache = KEGG_PATHWAY_NAMES
    conda:
        workflow.source_path("../env/py3.12.yaml")
    resources:
        **rule_resource(config, 'low_resource', skip_queue_on_local=True, logger=logger)
    log:
        "logs/06.merge/export_rnaflow_annotation.log"
    benchmark:
        "benchmarks/06.merge/export_rnaflow_annotation.txt"
    message:
        "📤 Exporting RNAFlow-ready annotation & KEGG pathway names"
    shell:
        """
        python3 "{EXPORT_RNAFLOW_ANNOTATION}" \
            --input {input.eggnog:q} \
            --output-annotation {output.annotation:q} \
            --output-names {output.pathway_names:q} \
            --names-cache {params.names_cache:q} \
            > {log} 2>&1
        """
