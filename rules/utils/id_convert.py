#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AnnoFlow Sample Sheet Parser
=============================
样本表解析（Flow framework §8.4 标准行为）：
读取 → 校验必填列 → 校验 sample 唯一性 → 构建 samples dict → fail-fast 列出问题。
"""

import csv

from utils.exceptions import SampleSheetError


def load_samples(csv_path, required_cols=("sample",), index_col="sample"):
    """
    读取样本表 CSV 并返回 samples 字典。

    Args:
        csv_path: 样本表路径（必须存在，缺失即 fail-fast）
        required_cols: 必填列名集合
        index_col: 样本唯一标识列（文件命名用，不得重复、不得含空格）

    Returns:
        dict: {sample_id: {col: value, ...}}

    Raises:
        SampleSheetError: 文件缺失 / 缺列 / ID 重复
    """
    if not csv_path:
        raise SampleSheetError(
            "配置缺少 sample_csv（样本表路径）。请在 analysisyaml 中以绝对路径指定，"
            "参考 config/samples.csv 模板。"
        )

    if not isinstance(csv_path, str) or not csv_path.strip():
        raise SampleSheetError(f"sample_csv 路径非法: {csv_path!r}")

    import os

    if not os.path.exists(csv_path):
        raise SampleSheetError(f"找不到样本表文件: {csv_path}")

    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(
            (line for line in f if not line.lstrip().startswith("#")),
            skipinitialspace=True,
        )
        fieldnames = reader.fieldnames or []
        rows = [
            {k: (v.strip() if isinstance(v, str) else v) for k, v in row.items()}
            for row in reader
            if any(v for v in row.values())
        ]

    missing = [c for c in required_cols if c not in fieldnames]
    if missing:
        raise SampleSheetError(
            f"样本表缺失必填列: {missing}（实际列: {fieldnames}），文件: {csv_path}"
        )

    samples = {}
    duplicated = []
    for row in rows:
        sid = row.get(index_col, "")
        if not sid:
            continue
        if sid in samples:
            duplicated.append(sid)
        samples[sid] = row

    if duplicated:
        raise SampleSheetError(f"样本 ID 重复: {sorted(set(duplicated))}（列 '{index_col}'）")

    if not samples:
        raise SampleSheetError(f"样本表为空（无有效数据行）: {csv_path}")

    return samples


__all__ = ["load_samples"]
