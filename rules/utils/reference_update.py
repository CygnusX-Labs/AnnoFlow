#!/usr/bin/env python3
# *---utf-8---*
"""
AnnoFlow Reference Path Resolution
===================================
注释数据库路径集中解析（Flow framework §2.4 / §3.1.1）：
reference.yaml 中相对 reference_path 的键解析为绝对路径；
check_reference_paths 对启用模块消费的键做存在性 fail-fast 校验。
"""

import os

from utils.exceptions import ReferenceError

DB_PATH_KEYS = ("eggnog_data_dir", "kofam_ko_list", "kofam_profiles")


def resolve_reference_paths(config, index_keys=DB_PATH_KEYS, base_path=None):
    """
    将 reference.yaml 中的相对路径键解析为绝对路径（原地更新 config）。

    Args:
        config (dict): Snakemake 全局 config
        index_keys: 需要解析的键（本流程即 DB_PATH_KEYS）
        base_path: 解析根目录；缺省读 config["reference_path"]

    Raises:
        ReferenceError: 配置了相对路径但 reference_path 为空
    """
    root = base_path or config.get("reference_path") or ""
    if root:
        root = os.path.abspath(os.path.expanduser(root))

    for key in index_keys:
        value = config.get(key)
        if not value:
            continue
        if os.path.isabs(os.path.expanduser(value)):
            config[key] = os.path.abspath(os.path.expanduser(value))
            continue
        if not root:
            raise ReferenceError(
                f"'{key}' 是相对路径 '{value}'，但 reference_path 未配置。"
                f"请在 analysisyaml 中设置 reference_path（绝对路径），"
                f"或把 '{key}' 写成绝对路径。"
            )
        config[key] = os.path.join(root, value)

    if root:
        config["reference_path"] = root

    return config


def check_reference_paths(config, logger=None):
    """
    校验启用模块实际消费的参考路径存在（fail-fast，§7.1 对齐原则：
    只校验当前启用模块消费的键，不因未使用条目退出）。

    Raises:
        ReferenceError: 列出全部缺失路径
    """
    module_keys = {
        "eggnog": ["eggnog_data_dir"],
        "kofamscan": ["kofam_ko_list", "kofam_profiles"],
    }

    missing = []
    for module, keys in module_keys.items():
        if config.get(module) is False:
            continue
        for key in keys:
            path = config.get(key)
            if not path:
                missing.append(f"[{key}] 未配置（模块 {module} 已启用）")
            elif not os.path.exists(path):
                missing.append(f"[{key}] {path} 不存在（模块 {module} 已启用）")

    if missing:
        message = "参考数据库路径校验失败：\n  " + "\n  ".join(missing)
        if logger:
            logger.error(message)
        raise ReferenceError(message + "\n请准备数据库目录并在 analysisyaml 中配置 reference_path。")

    if logger:
        logger.info("Reference database paths validated.")


__all__ = ["DB_PATH_KEYS", "resolve_reference_paths", "check_reference_paths"]
