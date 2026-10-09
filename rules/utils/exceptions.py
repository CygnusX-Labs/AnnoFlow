#!/usr/bin/env python3
# *---utf-8---*
"""
AnnoFlow Custom Exceptions
===========================
统一异常体系（Flow framework §9.3）：库代码禁止 sys.exit，
统一抛自定义异常，由 snakefile 顶层捕获后友好退出。
"""


class AnnoFlowError(Exception):
    """AnnoFlow 异常基类。"""


class ConfigError(AnnoFlowError):
    """配置加载或校验错误。"""


class SampleSheetError(AnnoFlowError):
    """样本表格式或内容错误。"""


class ReferenceError(AnnoFlowError):
    """参考数据库路径解析或校验错误。"""


__all__ = ["AnnoFlowError", "ConfigError", "SampleSheetError", "ReferenceError"]
