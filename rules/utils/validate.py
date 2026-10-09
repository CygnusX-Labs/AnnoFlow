#!/usr/bin/env python3
# *---utf-8---*
"""
AnnoFlow Configuration Validation Utilities
============================================
用户配置合并（analysisyaml 优先级链 §3.1）与校验。
"""

import os

import yaml

from utils.exceptions import ConfigError


def load_user_config(config, cmd_arg_name="analysisyaml"):
    """
    解析命令行传入的项目级配置文件路径，并递归合并进当前 config。

    优先级（低 → 高）：config 四件套 → analysisyaml → --config key=value

    Args:
        config (dict): Snakemake 全局 config 对象（原地合并）
        cmd_arg_name (str): 命令行 --config 的键名，默认 "analysisyaml"

    Raises:
        ConfigError: 文件不存在或 YAML 解析失败
    """
    custom_path = config.get(cmd_arg_name)

    if not custom_path:
        return

    if not os.path.exists(custom_path):
        raise ConfigError(
            f"Cannot find the specified analysisyaml: {custom_path}\n"
            f"请检查路径是否正确，或通过 --config {cmd_arg_name}=/path/to/project.yaml 传入。"
        )

    print(f"[Config Info] Loading project configuration: {custom_path}")

    try:
        with open(custom_path, "r") as f:
            custom_data = yaml.safe_load(f)
    except Exception as e:
        raise ConfigError(f"Failed to parse analysisyaml '{custom_path}': {e}")

    if not custom_data:
        print(f"[Config Warning] {custom_path} is empty, skipping.")
        return

    def _merge(base, update):
        for key, value in update.items():
            if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                _merge(base[key], value)
            else:
                base[key] = value

    _merge(config, custom_data)


def validate_species(config):
    """
    校验物种信息非空（AI taxonomy 判断与报告依赖）。
    """
    species = config.get("species", "")
    if not species or not str(species).strip():
        raise ConfigError(
            "配置缺少 species（物种名）。请在 analysisyaml 中设置，如 species: Dioscorea_alata"
        )
    return species


__all__ = ["load_user_config", "validate_species"]
