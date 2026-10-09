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

rule merge_summary_report:
    """
    Generate comprehensive summary report.
    """
    input:
        eggnog_stats = "03.merge/eggnog_stats.txt",
        kofam_stats = "03.merge/kofam_stats.txt",
        kegg_consistency_stats = "03.merge/kegg_consistency_stats.txt"
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

        cat >> {output.report} << 'EOF'

Annotation counting and selection standards:
1. Total means unique protein query IDs in the tool's processed table. It must not be calculated as With KEGG + With GO, because these are overlapping subsets.
2. eggNOG high-confidence records are rows classified as High (score >= 80), while also passing configured E-value, Bit-score, and optional required-annotation filters.
3. KofamScan high-confidence records are the best KO hit per protein that passes the KofamScan significance threshold and score requirement.
4. For downstream enrichment, use *_highconf.tsv by default. For stronger evidence, use proteins marked as KO一致 in kegg_consistency.tsv (same KO in both tools); treat KO冲突 as requiring manual review.
EOF

        echo "" >> {output.report}
        echo "================================================================================" >> {output.report}
        echo "Output Files:" >> {output.report}
        echo "  - 03.merge/eggnog_all_samples.tsv" >> {output.report}
        echo "  - 03.merge/kofam_all_samples.tsv" >> {output.report}
        echo "  - 03.merge/kegg_consistency.tsv" >> {output.report}
        echo "  - 03.merge/kegg_consistency_stats.txt" >> {output.report}
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
