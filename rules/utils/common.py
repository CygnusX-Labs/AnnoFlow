#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AnnoFlow Target Generation
===========================
分层目标生成（Flow framework §5.1 强制结构）：
AnalysisTargets() 计算分析目标 → DataDeliver() 追加交付/报告目标。
硬约束（§5.6）：纯函数（不改 config / 不 sleep / 不做 IO）、
目标列表只在 snakefile 计算一次、deliver/report 必须进 rule all。
"""

from utils import datadeliver
from utils.logger import get_pipeline_logger

logger = get_pipeline_logger()

# ─── 模块依赖图（自动启用缺失依赖并告警，§5.2）────────────────────────
MODULE_DEPENDENCIES = {
    "eggnog": [],
    "kofamscan": [],
    "integrate": ["eggnog", "kofamscan"],
    "merge": ["integrate"],
    "ai": ["integrate"],
}

# ─── 模块目标收集器注册表（顺序即收集顺序）────────────────────────────
MODULE_COLLECTORS = {
    "eggnog": datadeliver.eggnog,
    "kofamscan": datadeliver.kofamscan,
    "integrate": datadeliver.integrate,
    "merge": datadeliver.merge,
    "ai": datadeliver.ai,
}

# 固定目标：所有流程必须包含（输入 MD5 门控产物，§4）
FIXED_TARGETS = ["01.qc/md5_check.tsv"]


def _resolve_enabled_modules(config):
    """解析模块开关（config.get(module) is not False），自动启用缺失依赖。"""
    enabled = set()
    for module in MODULE_DEPENDENCIES:
        if config.get(module) is not False:
            enabled.add(module)

    changed = True
    while changed:
        changed = False
        for module in list(enabled):
            for dep in MODULE_DEPENDENCIES.get(module, []):
                if dep not in enabled:
                    logger.warning(f"Module '{module}' requires '{dep}', auto-enabling it.")
                    enabled.add(dep)
                    changed = True

    return enabled


def AnalysisTargets(config, samples, groups=None, contrasts=None):
    """
    计算所有启用分析模块的中间目标文件列表（纯函数，§5.6）。

    1. 固定追加 MD5 门控目标
    2. 解析模块开关 + 自动启用依赖
    3. 按 MODULE_COLLECTORS 顺序收集目标

    Returns:
        list[str]
    """
    targets = list(FIXED_TARGETS)

    enabled = _resolve_enabled_modules(config)

    for module, collector in MODULE_COLLECTORS.items():
        if module in enabled:
            targets = collector(samples, targets, config, groups=groups, contrasts=contrasts)

    if config.get("print_target"):
        logger.info(f"Targets ({len(targets)}):\n" + "\n".join(map(str, targets)))

    return targets


def DataDeliver(config, samples, groups=None, contrasts=None):
    """
    最终目标生成器，作为 rule all 的 input（纯函数，§5.6）。

    1. AnalysisTargets() 获取分析目标
    2. deliver=True 追加交付目标
    3. report=True 追加报告目标
    """
    targets = AnalysisTargets(config, samples, groups, contrasts)

    if config.get("deliver") is not False:
        targets.extend(datadeliver.delivery_outputs(config))

    if config.get("report") is not False:
        targets.extend(datadeliver.report_outputs(config))

    return targets


__all__ = [
    "MODULE_DEPENDENCIES",
    "MODULE_COLLECTORS",
    "FIXED_TARGETS",
    "AnalysisTargets",
    "DataDeliver",
]
