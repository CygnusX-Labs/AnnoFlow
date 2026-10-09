# =============================================================================
# AnnoFlow - Common Rules and Functions（Flow framework §6.1 通用模板层）
# =============================================================================
# 职责：导入公共函数 + 初始化 logger + 输入文件解析辅助函数。
# 本文件不定义任何业务 rule；业务 rule 从 03.* 开始编号。
# =============================================================================

import os
import glob

from utils.common import (
    AnalysisTargets,
    DataDeliver,
    MODULE_DEPENDENCIES,
    MODULE_COLLECTORS,
    FIXED_TARGETS,
)
from utils.logger import get_pipeline_logger

logger = get_pipeline_logger()

# -----------------------------------------------------------------------------
# 输入蛋白序列文件解析
# -----------------------------------------------------------------------------

INPUT_EXTENSIONS = (".pep", ".fa", ".fasta", ".faa", ".protein")


def find_input_file(sample):
    """
    按样本名在 INPUT_DIR 中解析输入蛋白序列文件。

    匹配顺序：
      1. sample 本身已带允许扩展名
      2. <sample><ext> 精确匹配
      3. <sample>*<ext> 复合扩展名匹配（如 .fa.TD2.1k.pep）
    都找不到时返回兜底路径 <sample>.pep（由 snakemake 报 MissingInput）。
    """
    base = sample

    for ext in INPUT_EXTENSIONS:
        if base.endswith(ext):
            path = os.path.join(INPUT_DIR, base)
            if os.path.exists(path):
                return path

    for ext in INPUT_EXTENSIONS:
        path = os.path.join(INPUT_DIR, f"{base}{ext}")
        if os.path.exists(path):
            return path

    for ext in INPUT_EXTENSIONS:
        candidates = glob.glob(os.path.join(INPUT_DIR, f"{base}*{ext}"))
        if candidates:
            return sorted(candidates)[0]

    return os.path.join(INPUT_DIR, f"{base}.pep")


def get_input_file(wildcards):
    """rule input 函数形式：按 wildcards.sample 解析输入文件。"""
    return find_input_file(wildcards.sample)


def get_all_input_files(wildcards=None):
    """全部样本输入文件列表（02 步 MD5 门控 rule 使用）。"""
    return [find_input_file(s) for s in SAMPLES]


def get_expected_md5_file(wildcards=None):
    """input_dir 中用户提供的期望 MD5 文件；不存在返回空串（只记录基线）。"""
    md5_name = config.get("raw_data", {}).get("md5", "md5.txt")
    candidate = os.path.join(INPUT_DIR, md5_name)
    return candidate if os.path.exists(candidate) else ""
