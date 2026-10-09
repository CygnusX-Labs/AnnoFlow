#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AnnoFlow Module Target Collectors
==================================
每个模块收集器返回的路径必须与对应 rule 的 output 逐字一致（§5.3）；
改 rule output 必须同 PR 改本文件对应收集器。
"""

import os


def eggnog(samples, data_deliver, config, **kwargs):
    """eggnog-mapper 注释产物（03.eggnog.smk）。"""
    for s in samples:
        data_deliver.append(f"01.eggnog/{s}_eggnog.tsv")
        data_deliver.append(f"01.eggnog/{s}_eggnog_highconf.tsv")
        data_deliver.append(f"01.eggnog/{s}_eggnog_report.txt")
    return data_deliver


def kofamscan(samples, data_deliver, config, **kwargs):
    """KofamScan 注释产物（04.kofamscan.smk）。"""
    for s in samples:
        data_deliver.append(f"02.kofam/{s}_kofam.tsv")
        data_deliver.append(f"02.kofam/{s}_kofam_highconf.tsv")
        data_deliver.append(f"02.kofam/{s}_kofam_report.txt")
    return data_deliver


def integrate(samples, data_deliver, config, **kwargs):
    """单样本整合评分与摘要（05.integrate.smk + 06.merge.smk 的 annotation_summary）。"""
    for s in samples:
        data_deliver.append(f"03.merge/{s}_integrated.tsv")
        data_deliver.append(f"03.merge/{s}_integrated_report.txt")
        data_deliver.append(f"03.merge/{s}_summary.txt")
    return data_deliver


def merge(samples, data_deliver, config, **kwargs):
    """多样本合并、一致性比对与总报告（06.merge.smk）。"""
    for f in [
        "03.merge/eggnog_all_samples.tsv",
        "03.merge/eggnog_highconf.tsv",
        "03.merge/eggnog_stats.txt",
        "03.merge/kofam_all_samples.tsv",
        "03.merge/kofam_highconf.tsv",
        "03.merge/kofam_stats.txt",
        "03.merge/kegg_consistency.tsv",
        "03.merge/kegg_consistency_stats.txt",
        "03.merge/SUMMARY_REPORT.txt",
    ]:
        data_deliver.append(f)
    return data_deliver


def ai(samples, data_deliver, config, **kwargs):
    """AI 逐蛋白评估产物（07.ai_curator.smk）。"""
    for s in samples:
        data_deliver.append(f"04.ai/{s}_ai_report.md")
        data_deliver.append(f"04.ai/{s}_ai_analysis.json")
        data_deliver.append(f"04.ai/{s}_ai_analysis.tsv")
        data_deliver.append(f"04.ai/{s}_ai_analysis.csv")
    data_deliver.append("04.ai/AI_MULTI_SAMPLE_SUMMARY.md")
    return data_deliver


def delivery_outputs(config):
    """交付模块固定输出（§5.4）。"""
    deliver_dir = config["data_deliver"]
    return [
        os.path.join(deliver_dir, "delivery_manifest.json"),
        os.path.join(deliver_dir, "delivery_manifest.md5"),
        os.path.join(deliver_dir, "delivery_details.log"),
    ]


def report_outputs(config):
    """报告模块固定输出（§5.4 最小实现）。"""
    return ["project_summary.json"]


__all__ = [
    "eggnog",
    "kofamscan",
    "integrate",
    "merge",
    "ai",
    "delivery_outputs",
    "report_outputs",
]
