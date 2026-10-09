#!/usr/bin/env python3
# *---utf-8---*
"""
AnnoFlow Resource Manager
==========================
HPC 资源 profile 解析（Flow framework §9.1）：
从 cluster_config.yaml 的 resource_profiles 取命名 profile；
local 模式只移除队列类键、必须保留 threads；
cluster 模式 queue_type 经 clusters 映射，缺失即 fail-fast（§3.4）。
"""

from utils.exceptions import ConfigError


def rule_resource(config, profile_name="default", skip_queue_on_local=True, logger=None):
    """
    从 cluster_config.yaml 的 resource_profiles 中获取命名 profile。

    Args:
        config: Snakemake config
        profile_name: "low_resource" | "default" | "high_resource" | "very_high_resource"
        skip_queue_on_local: local 模式下移除 queue_type（threads 必须保留）
        logger: 可选日志记录器

    Returns:
        dict: {"threads": N, "mem_mb": N, "runtime": N, ("queue": name)}

    Raises:
        ConfigError: profile 未定义 / cluster 模式 clusters 映射缺失
    """
    profiles = config.get("resource_profiles", {})

    if profile_name not in profiles:
        raise ConfigError(
            f"未知资源 profile '{profile_name}'，cluster_config.yaml 中可用: {sorted(profiles)}"
        )

    resource = dict(profiles[profile_name])

    if config.get("execution_mode", "local") == "cluster":
        queue_type = resource.get("queue_type")
        clusters = config.get("clusters", {})
        if queue_type not in clusters:
            raise ConfigError(
                f"cluster 模式下 queue_type '{queue_type}' 在 cluster_config.yaml 的 "
                f"clusters 映射中不存在（可用: {sorted(clusters)}），禁止静默降级（§3.4）。"
            )
        resource["queue"] = config.get("queue_id") or clusters[queue_type]
    elif skip_queue_on_local:
        resource.pop("queue_type", None)

    if logger:
        logger.debug(f"Resource allocation: {profile_name} -> {resource}")

    return resource


__all__ = ["rule_resource"]
