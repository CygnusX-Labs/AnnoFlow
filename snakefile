#!/usr/bin/env python3
# *---utf-8---*
# Pipeline: AnnoFlow（基因功能注释流程，Flow 家族成员）
# Version: 见 config/config.yaml 的 pipeline_version（版本唯一来源，§2.1）
# Author: JZHANG
"""
AnnoFlow - Gene Functional Annotation Pipeline
==============================================
eggnog-mapper（KEGG/GO/COG/EC/Pfam/CAZy）+ KofamScan 双工具注释、
质量过滤、可信度评估、结果整合、AI 逐蛋白可靠性分析。

Flow framework 标准运行方式（§2.3）:
    snakemake -s /path/to/AnnoFlow/snakefile \
        --cores 8 --use-conda --conda-frontend mamba \
        --rerun-triggers mtime \
        --logger rich-loguru \
        --config analysisyaml=/path/to/project.yaml

模块开关（config.yaml 显式默认值，§3.3）:
    eggnog / kofamscan / integrate / merge / ai / deliver / report
"""

import sys
import os

# ---- Import 路径准备：同时支持 rules.utils.*（入口）与 utils.*（内部，§2.2）----
try:
    _BASE_DIR = os.path.abspath(workflow.basedir)
except Exception:
    _BASE_DIR = os.getcwd()
for _p in (os.path.join(_BASE_DIR, "rules"), _BASE_DIR):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from snakemake.utils import min_version, validate

# ─── Step 1: 导入框架工具 ───────────────────────────────────────────
from rules.utils.id_convert import load_samples
from rules.utils.validate import load_user_config, validate_species
from rules.utils.reference_update import (
    DB_PATH_KEYS,
    resolve_reference_paths,
    check_reference_paths,
)
from rules.utils.resource_manager import rule_resource
from rules.utils.logger import get_pipeline_logger
from rules.utils.common import AnalysisTargets, DataDeliver, MODULE_DEPENDENCIES
from rules.utils.exceptions import AnnoFlowError, SampleSheetError

# Lock Snakemake Version
min_version("9.9.0")

# ─── Step 2: 加载默认四件套 ─────────────────────────────────────────
configfile: "config/config.yaml"
configfile: "config/reference.yaml"
configfile: "config/run_parameter.yaml"
configfile: "config/cluster_config.yaml"

# ─── Step 3: 用户 analysisyaml 覆盖（最高优先级）────────────────────
# ─── Step 4: 解析参考数据库路径 ─────────────────────────────────────
# ─── Step 5: Schema 验证 + 参考路径 fail-fast ───────────────────────
logger = get_pipeline_logger()

try:
    load_user_config(config, cmd_arg_name="analysisyaml")
    resolve_reference_paths(config, DB_PATH_KEYS, base_path=config.get("reference_path"))
    validate(config, "schema/config.schema.yaml")
    validate_species(config)
    check_reference_paths(config, logger=logger)
except AnnoFlowError as e:
    print(f"\n\033[91m[AnnoFlow Config Error]\033[0m {e}\n", file=sys.stderr)
    sys.exit(1)

logger.info("Configuration loaded and validated")

# ─── Step 6: 工作目录重定向 ─────────────────────────────────────────
workdir: config["workflow"]
logger.info(f"Redirect workspaces to {config['workflow']}")

# ─── Step 7: 加载样本表 ─────────────────────────────────────────────
# sample_csv 必须为绝对路径：解析发生在 workdir 重定向前（§3.2 已验证的坑）
try:
    _SAMPLES_DICT = load_samples(config.get("sample_csv"), required_cols=("sample",))
except SampleSheetError as e:
    print(f"\n\033[91m[AnnoFlow SampleSheet Error]\033[0m {e}\n", file=sys.stderr)
    sys.exit(1)

SAMPLES = list(_SAMPLES_DICT.keys())
GROUPS = None  # AnnoFlow 无分组/对比分析

# -----------------------------------------------------------------------------
# Flow 常量（配置 → 全局常量集中定义，供 rules/*.smk 使用）
# -----------------------------------------------------------------------------
INPUT_DIR = config["input_dir"]

EGGNOG_DATA_DIR = config["eggnog_data_dir"]
KOFAM_KO_LIST = config["kofam_ko_list"]
KOFAM_PROFILES = config["kofam_profiles"]

# KEGG ko##### 通路名缓存（ko_list 只有 KO 定义，不含通路名）。
# 缺省放在参考库 dataset/ 根目录；可用 kegg_pathway_names 覆盖（相对 reference_path 解析）。
_kegg_pathway_names = config.get("kegg_pathway_names")
if _kegg_pathway_names:
    KEGG_PATHWAY_NAMES = (_kegg_pathway_names if os.path.isabs(_kegg_pathway_names)
                          else os.path.join(config.get("reference_path", ""), _kegg_pathway_names))
else:
    KEGG_PATHWAY_NAMES = os.path.join(os.path.dirname(os.path.dirname(KOFAM_KO_LIST)),
                                      "kegg_pathway_names.tsv")

EGGNOG_CPU = config.get("eggnog_cpu", 8)
KOFAM_CPU = config.get("kofam_cpu", 8)

EVALUE_THRESHOLD = config.get("evalue_threshold", 1e-5)
BITSCORE_THRESHOLD = config.get("bitscore_threshold", 60)
MIN_CONFIDENCE = config.get("min_confidence", "High")
REQUIRE_KEGG = config.get("require_kegg", True)
REQUIRE_GO = config.get("require_go", False)

AI_CONFIG = config.get("ai_config", {})


def _resolve_script_path(script_path):
    """脚本相对路径基于 snakefile 目录解析为绝对路径。"""
    if not script_path:
        return None
    if os.path.isabs(script_path):
        return script_path
    return os.path.join(workflow.basedir, script_path)


_scripts = config.get("scripts", {})
EGGNOG_PROCESSOR = _resolve_script_path(_scripts.get("eggnog_processor", "scripts/eggnog_processor.py"))
KOFAMSCAN_PROCESSOR = _resolve_script_path(_scripts.get("kofamscan_processor", "scripts/kofamscan_processor.py"))
MERGE_RESULTS = _resolve_script_path(_scripts.get("merge_results", "scripts/merge_results.py"))
INTEGRATE_ANNOTATIONS = _resolve_script_path(_scripts.get("integrate_annotations", "scripts/integrate_annotations.py"))
COMPARE_KEGG = _resolve_script_path(_scripts.get("compare_kegg_annotations", "scripts/compare_kegg_annotations.py"))
EXPORT_ANNOTATION_SETS = _resolve_script_path(_scripts.get("export_annotation_sets", "scripts/export_annotation_sets.py"))
EXPORT_RNAFLOW_ANNOTATION = _resolve_script_path(_scripts.get("export_rnaflow_annotation", "scripts/export_rnaflow_annotation.py"))
AI_CURATOR = _resolve_script_path(_scripts.get("ai_curator", "scripts/ai_curator.py"))
CHECK_INPUT_MD5 = _resolve_script_path(_scripts.get("check_input_md5", "scripts/check_input_md5.py"))
DELIVER_SCRIPT = _resolve_script_path(_scripts.get("deliver", "scripts/deliver.py"))

# ─── Step 8 前置：目标列表只计算一次（§5.6），供 rule all / deliver / report 复用 ───
ALL_TARGETS = DataDeliver(config, SAMPLES, GROUPS)
_deliver_prefix = os.path.join(str(config.get("data_deliver", "")), "")
DELIVER_INPUTS = [t for t in ALL_TARGETS if not str(t).startswith(_deliver_prefix)]
REPORT_INPUTS = [t for t in DELIVER_INPUTS if str(t) != "project_summary.json"]

# ─── Step 8: 包含规则（编号连续，01-02 通用层 + 03-07 组学层 + 08-09 收尾层）───
include: "rules/01.common.smk"
include: "rules/02.input_md5.smk"
include: "rules/03.eggnog.smk"
include: "rules/04.kofamscan.smk"
include: "rules/05.integrate.smk"
include: "rules/06.merge.smk"
include: "rules/07.ai_curator.smk"
include: "rules/08.deliver.smk"
include: "rules/09.Report.smk"

# --------- Pipeline Initialization ---------
logger.info("=" * 60)
logger.info("AnnoFlow Started")
logger.info("=" * 60)
logger.info(f"Working directory: {config['workflow']}")
logger.info(f"Samples: {SAMPLES}")
logger.info(f"Input directory: {INPUT_DIR}")
_module_states = {k: (config.get(k) is not False) for k in MODULE_DEPENDENCIES}
logger.info(f"Modules: {_module_states}")
logger.info("=" * 60)


# --------- Target Rules ---------
rule all:
    """
    默认目标：DataDeliver() 生成的全部分析 + 交付 + 报告目标（§5.1 分层）。
    """
    input:
        ALL_TARGETS,
    message:
        "✅ AnnoFlow complete! All outputs generated."


rule annotate:
    """
    仅运行注释（eggnog + KofamScan 处理结果）:
        snakemake ... annotate
    """
    input:
        expand("01.eggnog/{sample}_eggnog.tsv", sample=SAMPLES),
        expand("02.kofam/{sample}_kofam.tsv", sample=SAMPLES),
    message:
        "✅ Annotation complete for all samples"


rule merge:
    """
    多样本合并与汇总:
        snakemake ... merge
    """
    input:
        "03.merge/eggnog_all_samples.tsv",
        "03.merge/kofam_all_samples.tsv",
        "03.merge/kegg_consistency.tsv",
        "03.merge/kegg_shared.tsv",
        "03.merge/SUMMARY_REPORT.txt",
    message:
        "✅ Results merged successfully"


rule reports:
    """
    生成全部分析摘要（不含 project_summary.json，走 rule all 或 report 目标）:
        snakemake ... reports
    """
    input:
        expand("03.merge/{sample}_summary.txt", sample=SAMPLES),
        "03.merge/SUMMARY_REPORT.txt",
    message:
        "✅ Reports generated for all samples"


rule ai_analysis:
    """
    AI 逐蛋白评估（需模块开关 ai: true）:
        snakemake ... --config ai=true ai_analysis
    """
    input:
        expand("04.ai/{sample}_ai_report.md", sample=SAMPLES),
        "04.ai/AI_MULTI_SAMPLE_SUMMARY.md",
    message:
        "🤖 AI analysis complete!"
