# AnnoFlow 使用指南

本文档说明 AnnoFlow 的配置体系、常用命令、测试数据、处理脚本的独立使用方法，以及从旧版的迁移要点。

- 数据库准备见 [database_preparation.md](database_preparation.md)
- 流程结构与结果解读见 [pipeline.md](pipeline.md)
- AI 逐蛋白评估见 [ai_analysis.md](ai_analysis.md)

---

## 配置体系

### 配置优先级链

```
config 四件套（仓库默认值） < analysisyaml（项目级） < --config key=value（命令行）
```

四件套位于 `config/`：

| 文件 | 职责 |
|------|------|
| `config.yaml` | 流程控制：`pipeline_version`、`log_level`、`execution_mode`、输入门控（`raw_data.md5`，默认 `md5.txt`）、模块开关、`ai_config` 段、`scripts` 脚本路径表 |
| `reference.yaml` | 数据库参考路径（相对 `reference_path` 解析）；`reference_path` 入库默认为空，站点真实路径经 analysisyaml 覆盖 |
| `run_parameter.yaml` | 线程数与过滤阈值 |
| `cluster_config.yaml` | HPC 资源 profile 与队列映射（`execution_mode: cluster` 时经 `--profile` 消费；local 模式仅作参考） |

项目级差异一律写入 analysisyaml（模板：`examples/analysisyaml.example.yaml`），保持仓库默认值不动。

### run_parameter.yaml（线程与阈值）

```yaml
eggnog_cpu: 8                # eggnog-mapper 线程数
kofam_cpu: 8                 # KofamScan 线程数
evalue_threshold: 1.0e-5     # E-value 阈值（越小越严格）
bitscore_threshold: 60       # Bit-score 阈值（越大越严格）
min_confidence: "High"       # 最低可信度: High | Medium | Low
require_kegg: true           # 是否要求必须有 KEGG 注释
require_go: false            # 是否要求必须有 GO 注释
```

### analysisyaml 必填七项

schema 强制验证，其中五个路径键**必须绝对路径**（样本表解析发生在 workdir 重定向前）：

```yaml
project_name: my_annotation_project
species: Dioscorea_alata
sample_csv: /data/project/01.workflow/samples.csv   # 参照 config/samples.csv 模板
workflow: /data/project/01.workflow                 # 工作目录（Snakemake workdir）
data_deliver: /data/project/02.data_deliver
input_dir: /data/project/00.protein                 # 输入蛋白序列目录
reference_path: /data/jzhang/reference/AnnoFlow
```

### 样本表 samples.csv

模板见 `config/samples.csv`。`sample` 为唯一标识（用于文件命名，不得重复、不得含空格），`sample_name` 为显示名称（可选，用于报告）。支持复合扩展名匹配：样本写 `TD2.1k`，实际文件可为 `TD2.1k.pep`、`TD2.1k.fa` 或 `TD2.1k.fa.TD2.1k.pep`。

```csv
sample,sample_name
TD2.1k,TD2.1k
```

### 模块开关

`config/config.yaml` 中每个模块都有显式布尔开关（默认值必须显式写出）：

| 模块 | 默认 | 说明 |
|------|------|------|
| eggnog | true | eggnog-mapper 功能注释（KEGG/GO/COG/EC/Pfam/CAZy） |
| kofamscan | true | KofamScan KO 注释 |
| integrate | true | 双工具整合评分与冲突裁决 |
| merge | true | 多样本合并、KO 一致性比对与汇总 |
| ai | false | AI 逐蛋白可靠性评估（需配置 `ai_config`） |
| deliver | true | 交付 delivery_manifest（copy 模式） |
| report | true | `project_summary.json` 最小报告 |

依赖自动启用：integrate 依赖 eggnog + kofamscan，merge 依赖 integrate，ai 依赖 integrate——开启下游模块时缺失的上游会被自动打开并记录警告日志。任一开关设为 `false`，其产物目标即从 DAG 中消失。

**关闭模块请写进 analysisyaml，不要用 `--config` 传布尔值**——`--config merge=false` 中的 `false` 会被解析为字符串，非空字符串恒为真，模块关不掉（本流程以 `config.get(k) is not False` 判定开关）：

```yaml
# project.yaml 中关闭 merge（eggnog/kofamscan/integrate/ai/deliver/report 同理）：
merge: false
```

标量参数（如 `evalue_threshold`）仍可用 `--config key=value` 临时覆盖，分析级设置建议一律写 analysisyaml。

### 交付与报告

- **deliver**（默认开）：产物 copy 到 `data_deliver`，生成 `delivery_manifest.json`（来源、大小、MD5、动作）、`delivery_manifest.md5`、`delivery_details.log`
- **report**（默认开）：生成 `project_summary.json`（项目元数据、样本列表、模块启用状态、关键产物清单）

### 监控推送（可选）

`monitor_config.yaml` 为 OmicHub 工作流监控推送配置模板，与 `--logger rich-loguru` 配套使用；token 等敏感值一律用 `${ENV_VAR}` 引用环境变量，禁止写真实值。

---

## 常用命令

标准运行方式：

```bash
snakemake -s /path/to/AnnoFlow/snakefile --cores 8 --use-conda --conda-frontend mamba \
  --rerun-triggers mtime --logger rich-loguru \
  --config analysisyaml=/path/to/project.yaml
```

```bash
# 1. dry-run：查看执行计划（不实际运行），同时暴露配置/路径错误
snakemake -s /path/to/AnnoFlow/snakefile -n --config analysisyaml=/path/to/project.yaml

# 2. 仅运行注释（eggnog + KofamScan 处理结果）
snakemake -s /path/to/AnnoFlow/snakefile --cores 8 --use-conda --conda-frontend mamba \
  --config analysisyaml=/path/to/project.yaml annotate

# 3. 仅运行 AI 分析（需 analysisyaml 中 ai: true，且已有注释结果）
snakemake -s /path/to/AnnoFlow/snakefile --cores 8 --use-conda --conda-frontend mamba \
  --config analysisyaml=/path/to/project.yaml ai_analysis

# 4. 仅合并多样本结果
snakemake -s /path/to/AnnoFlow/snakefile --cores 4 --use-conda --conda-frontend mamba \
  --config analysisyaml=/path/to/project.yaml merge

# 5. 仅生成分析摘要（单样本 summary + SUMMARY_REPORT.txt，不含 project_summary.json）
snakemake -s /path/to/AnnoFlow/snakefile --cores 4 --use-conda --conda-frontend mamba \
  --config analysisyaml=/path/to/project.yaml reports

# 6. 生成 DAG 图
snakemake -s /path/to/AnnoFlow/snakefile --config analysisyaml=/path/to/project.yaml \
  --dag | dot -Tpng > dag.png
```

---

## 示例分析：test/TD2.1k.pep

**样本信息**: 1000 条蛋白质序列（转录组 ORF 预测产物，含复合命名格式的 FASTA 头）

**最小可运行配置**:

```yaml
# project.yaml
project_name: annoflow_test
species: test_species
sample_csv: /path/to/samples.csv    # 内容：TD2.1k,TD2.1k（test/ 同结构）
workflow: /path/to/test_workdir
data_deliver: /path/to/test_deliver
input_dir: /path/to/AnnoFlow/test   # 含 TD2.1k.pep
reference_path: /data/jzhang/reference/AnnoFlow
```

**运行**:

```bash
snakemake -s /path/to/AnnoFlow/snakefile --cores 4 --use-conda --conda-frontend mamba \
  --rerun-triggers mtime --logger rich-loguru \
  --config analysisyaml=project.yaml
```

**查看结果**: `01.qc/md5_check.tsv`（输入校验）→ `01.eggnog/TD2.1k_eggnog_report.txt`（过滤统计）→ `03.merge/SUMMARY_REPORT.txt`（整体汇总）→ `project_summary.json`（项目摘要）。

---

## 脚本独立使用

各脚本可脱离 Snakemake 单独运行（环境：`env/py3.12.yaml`）。

### eggnog_processor.py

```bash
# 基本用法
python3 scripts/eggnog_processor.py \
    -i 01.eggnog/TD2.1k.emapper.annotations \
    -o 01.eggnog/TD2.1k_eggnog

# 高可信度 + KEGG 过滤
python3 scripts/eggnog_processor.py \
    -i test.emapper.annotations \
    -o filtered \
    --min-confidence High \
    --require-kegg

# 自定义阈值
python3 scripts/eggnog_processor.py \
    -i test.emapper.annotations \
    -o strict_filtered \
    --evalue 1e-10 \
    --bitscore 80
```

### kofamscan_processor.py

```bash
python3 scripts/kofamscan_processor.py \
    -i 02.kofam/TD2.1k_kofam_detail.txt \
    -o 02.kofam/TD2.1k_kofam \
    -e 01.eggnog/TD2.1k.emapper.annotations \
    --min-confidence High
```

### integrate_annotations.py

```bash
python3 scripts/integrate_annotations.py \
    -e 01.eggnog/TD2.1k_eggnog.tsv \
    -k 02.kofam/TD2.1k_kofam.tsv \
    -s TD2.1k \
    -o 03.merge/TD2.1k
```

### merge_results.py

```bash
# 合并 eggnog 结果
python3 scripts/merge_results.py \
    --input-dir 01.eggnog \
    --samples sample1 sample2 sample3 \
    --tool eggnog \
    --output-all 03.merge/eggnog_all.tsv \
    --output-high 03.merge/eggnog_high.tsv \
    --output-stats 03.merge/eggnog_stats.txt

# 合并 kofam 结果
python3 scripts/merge_results.py \
    --input-dir 02.kofam \
    --samples sample1 sample2 sample3 \
    --tool kofam \
    --output-all 03.merge/kofam_all.tsv \
    --output-high 03.merge/kofam_high.tsv \
    --output-stats 03.merge/kofam_stats.txt
```

### export_rnaflow_annotation.py

```bash
python3 scripts/export_rnaflow_annotation.py \
    --input 03.merge/eggnog_all_samples.tsv \
    --output-annotation 03.merge/rnaflow_annotation.tsv \
    --output-names 03.merge/kegg_pathway_names.tsv \
    --names-cache <reference_path>/dataset/kegg_pathway_names.tsv
```

`--names-cache` 可省略：缓存不存在时自动从 KEGG REST 拉取；完全离线时通路名映射为空（告警但不失败）。可对**已有运行目录**直接补跑，无需重跑整个流程。名称解析顺序与缓存机制详见 [database_preparation.md](database_preparation.md)。

---

## 从旧版迁移

本流程由早期 KEGG 注释流程（kegg annotation pipeline 仓库）重构而来并更名 AnnoFlow。旧项目升级要点：

| 旧版 | AnnoFlow |
|------|----------|
| `conf` 目录四份配置（config / resource / parameter / ai） | `config` 目录四件套：`config.yaml`（默认）+ `reference.yaml` + `run_parameter.yaml` + `cluster_config.yaml`；项目级差异写入 analysisyaml |
| 根目录示例配置 | `examples/analysisyaml.example.yaml` |
| 配置里的 `samples:` 样本列表 | 样本表 CSV（模板 `config/samples.csv`，两列 `sample,sample_name`），经 `sample_csv` 指定 |
| AI 的 `enabled` 开关（`ai` 段内） | 顶层模块开关 `ai: true` + 同级 `ai_config:` 段（provider / model / api_key / api_base / taxonomy / max_proteins / no_auto_filter） |
| 大写驼峰命名的 KofamScan 处理脚本 | `scripts/kofamscan_processor.py`（全小写） |
| 通用 Python 环境文件（基于 python3 命名） | `env/py3.12.yaml` |
| 规则文件 02.config / 08.report | 已删除：配置集中在 snakefile 入口，规则重新编号 01-09，新增 02.input_md5（MD5 门控）、08.deliver（交付）、09.Report |
| 100 条蛋白的旧测试样本 | `test/TD2.1k.pep`（1000 条蛋白序列） |
| 直接 `snakemake --use-conda` | 标准命令：`-s <AnnoFlow>/snakefile --use-conda --conda-frontend mamba --rerun-triggers mtime --logger rich-loguru --config analysisyaml=<project.yaml>` |

迁移步骤：准备数据库目录（见 [database_preparation.md](database_preparation.md)）→ 将旧样本列表改写为 `samples.csv` → 按 `examples/analysisyaml.example.yaml` 填写七项必填配置 → dry-run 验证 → 正式运行。