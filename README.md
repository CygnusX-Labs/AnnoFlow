# AnnoFlow

基因功能注释流程（Flow 家族成员）：eggnog-mapper 提供 KEGG/GO/COG/EC/Pfam/CAZy 全功能注释，KofamScan 提供 KO 交叉验证，整合层做双工具冲突裁决，可选 AI 驱动的逐蛋白可靠性审核。基于 Snakemake + Conda，模块化设计、质量过滤、可信度评估、交付与报告一体化。

版本：`AnnoFlow v1.0.0`（唯一版本来源为 `config/config.yaml` 的 `pipeline_version`）。

## 项目特点

- ✅ **模块化设计**: 规则按步骤编号（01-09），每个模块可独立开关，关闭后目标自动从 DAG 消失
- ✅ **输入 MD5 硬性门控**: 所有样本输入校验通过才进入注释，防止用错/损坏的数据跑完整流程
- ✅ **质量过滤**: 基于 E-value、Bit-score 等多维度过滤
- ✅ **可信度评估**: 三级可信度分级 (High/Medium/Low)，0-100 分评分体系
- ✅ **结果整合**: 对 eggnog 和 KofamScan 结果进行横向整合与 KO 冲突裁决
- ✅ **多样本合并**: 支持多样本结果合并与 KEGG 一致性比对，便于下游分析
- ✅ **Conda 环境**: 自动管理依赖环境（mamba 加速），保证可重复性
- ✅ **AI 驱动分析**（可选）: 逐蛋白可靠性评估（Ollama/OpenAI/Claude），含分层筛选与 Token 消耗追踪
- ✅ **交付与报告**: 自动生成交付清单（manifest + MD5）与 `project_summary.json`
- ✅ **灵活输入**: 支持 `.pep`、`.fa`、`.fasta`、`.faa`、`.protein` 及复合扩展名（如 `.fa.TD2.1k.pep`）
- ✅ **Schema 强制验证**: 启动即校验项目配置，路径错误 fail-fast，不浪费集群资源

---

## 目录结构

```
.
├── snakefile                      # 主工作流：配置加载、schema 验证、目标生成
├── monitor_config.yaml            # OmicHub 监控推送配置模板（可选）
├── config/                        # 默认配置四件套 + 样本表模板
│   ├── config.yaml                # 流程控制：版本、模块开关、ai_config、脚本路径表
│   ├── reference.yaml             # 数据库参考路径（相对 reference_path 解析）
│   ├── run_parameter.yaml         # 线程数与过滤阈值
│   ├── cluster_config.yaml        # HPC 资源 profile 与队列映射
│   └── samples.csv                # 样本表模板（sample,sample_name）
├── schema/
│   └── config.schema.yaml         # 启动时强制验证的配置 schema
├── examples/
│   └── analysisyaml.example.yaml  # 项目级配置示例（复制修改后使用）
├── rules/                         # Snakemake 规则（按步骤编号 01-09）
│   ├── 01.common.smk              # 通用辅助函数（输入文件解析；无业务 rule）
│   ├── 02.input_md5.smk           # 输入 MD5 校验门控
│   ├── 03.eggnog.smk              # eggnog-mapper 注释与结果处理
│   ├── 04.kofamscan.smk           # KofamScan 注释与结果处理
│   ├── 05.integrate.smk           # eggnog + KofamScan 整合评分
│   ├── 06.merge.smk               # 多样本合并 / KO 一致性比对 / 汇总
│   ├── 07.ai_curator.smk          # AI 逐蛋白可靠性评估（可选）
│   ├── 08.deliver.smk             # 交付清单（delivery manifest）
│   ├── 09.Report.smk              # project_summary.json
│   └── utils/                     # 框架工具（目标生成、配置校验、资源、日志等 8 个模块）
├── scripts/                       # Python 处理脚本
│   ├── eggnog_processor.py
│   ├── kofamscan_processor.py
│   ├── integrate_annotations.py
│   ├── merge_results.py
│   ├── compare_kegg_annotations.py
│   ├── ai_curator.py
│   ├── check_input_md5.py
│   └── deliver.py
├── env/                           # Conda 环境配置
│   ├── eggnog-mapper.yaml
│   ├── kofamscan.yaml
│   ├── openai.yaml
│   └── py3.12.yaml
├── docs/
│   └── filtering_standards.md     # 过滤与可信度评估标准详解
└── test/
    └── TD2.1k.pep                 # 测试数据（1000 条蛋白序列）
```

---

## Flow 家族架构

AnnoFlow 对齐 Flow 框架规范，与家族内其他流程共享同一套运行约定。

### 模块开关与依赖自动启用

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

### 输入 MD5 硬性门控（rules/02.input_md5.smk）

所有样本输入文件必须完成 MD5 校验才生成 `01.qc/md5_check.tsv`；下游 `eggnog_mapper` / `kofamscan` 显式依赖该门控文件，校验不过根本不会启动比对。行为规则：

- `input_dir` 下存在 `md5.txt`（格式：`<md5><空格><文件名>`）→ 逐文件比对
- 无 `md5.txt` → 计算并记录基线，标记 PASS（SRA 兼容原则）
- 任一 FAIL 或输入文件缺失 → 立即非零退出，流程中止

### 配置四件套 + schema 验证

启动时的配置优先级链：

```
config 四件套（仓库默认值） < analysisyaml（项目级） < --config key=value（命令行）
```

四件套：`config/config.yaml`（流程控制）、`config/reference.yaml`（数据库路径）、`config/run_parameter.yaml`（线程与阈值）、`config/cluster_config.yaml`（资源 profile）。合并后经 `schema/config.schema.yaml` **强制验证**：必填 `project_name`、`species`、`sample_csv`、`workflow`、`data_deliver`、`input_dir`、`reference_path`，其中后五个路径键**必须绝对路径**（样本表解析发生在 workdir 重定向前）。参考数据库路径同时做 fail-fast 检查，dry-run 即可暴露路径错误。

### 交付与报告

- **deliver**（默认开）：产物 copy 到 `data_deliver`，生成 `delivery_manifest.json`（来源、大小、MD5、动作）、`delivery_manifest.md5`、`delivery_details.log`
- **report**（默认开）：生成 `project_summary.json`（项目元数据、样本列表、模块启用状态、关键产物清单）

### 监控推送（可选）

`monitor_config.yaml` 为 OmicHub 工作流监控推送配置模板，与 `--logger rich-loguru` 配套使用；token 等敏感值一律用 `${ENV_VAR}` 引用环境变量，禁止写真实值。

---

## 快速开始

### 1. 环境准备

确保已安装 [Snakemake](https://snakemake.readthedocs.io/)（9.9.0+）和 [Conda](https://docs.conda.io/)（推荐 Miniconda + mamba）：

```bash
conda install -n base -c conda-forge -c bioconda snakemake
```

### 2. 准备数据库目录

按参考目录约定部署数据库（本站实例：`/data/jzhang/reference/AnnoFlow`）：

```
<reference_path>/
├── dataset/eggnog-mapper/                  # eggnog-mapper 数据库（eggnog.db 等）
└── dataset/kegg_<date>_ko_dataset/
    ├── ko_list                             # KofamScan KO 阈值列表
    └── profiles/                           # KofamScan HMM profiles
```

### 3. 编写项目级配置（analysisyaml）

```bash
cp examples/analysisyaml.example.yaml /path/to/project.yaml
vim /path/to/project.yaml
```

填写 schema 必填的七项（五个路径键必须绝对路径）：

```yaml
project_name: my_annotation_project
species: Dioscorea_alata
sample_csv: /data/project/01.workflow/samples.csv   # 参照 config/samples.csv 模板
workflow: /data/project/01.workflow                 # 工作目录（Snakemake workdir）
data_deliver: /data/project/02.data_deliver
input_dir: /data/project/00.protein                 # 输入蛋白序列目录
reference_path: /data/jzhang/reference/AnnoFlow
```

样本表（`sample` 匹配 `input_dir` 下 `<sample>.pep/.fa/.fasta/.faa/.protein`，支持复合扩展名如 `.fa.TD2.1k.pep`）：

```csv
sample,sample_name
TD2.1k,TD2.1k
```

### 4. 运行

Flow 框架标准运行方式：

```bash
snakemake -s /path/to/AnnoFlow/snakefile --cores 8 --use-conda --conda-frontend mamba \
  --rerun-triggers mtime --logger rich-loguru \
  --config analysisyaml=/path/to/project.yaml
```

### 常用命令

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

**关闭模块请写进 analysisyaml，不要用 `--config` 传布尔值**——`--config merge=false` 中的 `false` 会被解析为字符串，非空字符串恒为真，模块关不掉（本流程以 `config.get(k) is not False` 判定开关）：

```yaml
# project.yaml 中关闭 merge（eggnog/kofamscan/integrate/ai/deliver/report 同理）：
merge: false
```

标量参数（如 `evalue_threshold`）仍可用 `--config key=value` 临时覆盖，分析级设置建议一律写 analysisyaml。

---

## 配置说明

### config/config.yaml

仓库级默认配置：流程控制（`pipeline_version`、`log_level`、`execution_mode`）、输入门控（`raw_data.md5`，期望的校验文件名，默认 `md5.txt`）、**模块开关**（见上表）、`ai_config` 段、`scripts` 脚本路径表。

### config/reference.yaml

数据库参考路径集中管理。`reference_path` 入库默认为空（占位），站点真实路径经 analysisyaml 覆盖；`eggnog_data_dir` / `kofam_ko_list` / `kofam_profiles` 相对 `reference_path` 解析（写成绝对路径则直接使用）。

### config/run_parameter.yaml

```yaml
eggnog_cpu: 8                # eggnog-mapper 线程数
kofam_cpu: 8                 # KofamScan 线程数
evalue_threshold: 1.0e-5     # E-value 阈值（越小越严格）
bitscore_threshold: 60       # Bit-score 阈值（越大越严格）
min_confidence: "High"       # 最低可信度: High | Medium | Low
require_kegg: true           # 是否要求必须有 KEGG 注释
require_go: false            # 是否要求必须有 GO 注释
```

### config/cluster_config.yaml

`resource_profiles` 定义 low_resource / default / high_resource / very_high_resource 四档（各含 threads / mem_mb / runtime / queue_type），`clusters` 段将 queue_type 映射为实际队列名。`execution_mode: cluster` 时经 `--profile`/调度插件消费；local 模式下资源 profile 仅作参考。

### 样本表 samples.csv

模板见 `config/samples.csv`。`sample` 为唯一标识（用于文件命名，不得重复、不得含空格），`sample_name` 为显示名称（可选，用于报告）。支持复合扩展名匹配：样本写 `TD2.1k`，实际文件可为 `TD2.1k.pep`、`TD2.1k.fa` 或 `TD2.1k.fa.TD2.1k.pep`。

---

## 分析流程详解

### 流程图

```
input_dir 下蛋白序列（<sample>.pep/.fa/.fasta/.faa/.protein，支持复合扩展名）
    │
    ▼  🔐 MD5 硬性门控（02.input_md5.smk）
01.qc/md5_check.tsv                ← 有 md5.txt 则比对，无则记录基线 PASS
    │
    ├── 03.eggnog.smk ──────────────────────────────┐
    │    eggnog_mapper ──► 01.eggnog/{sample}.emapper.annotations
    │    eggnog_processor ──► 01.eggnog/{sample}_eggnog.tsv           │
    │                         01.eggnog/{sample}_eggnog_highconf.tsv  │
    │                                                                 │
    ├── 04.kofamscan.smk ───────────────────────────┤
    │    kofamscan ──► 02.kofam/{sample}_kofam_detail.txt             │
    │    kofamscan_processor ──► 02.kofam/{sample}_kofam.tsv          │
    │                            02.kofam/{sample}_kofam_highconf.tsv │
    │                                                                 │
    ├── 05.integrate.smk ───────────────────────────┤
    │    integrate_annotations ──► 03.merge/{sample}_integrated.tsv   │
    │                              03.merge/{sample}_integrated_report│
    │                                                                 │
    ├── 06.merge.smk ───────────────────────────────┤
    │    merge_eggnog_results / merge_kofam_results ──► 03.merge/*_all_samples.tsv
    │    compare_kegg_annotations ──► 03.merge/kegg_consistency.tsv   │
    │    annotation_summary / merge_summary_report ──► {sample}_summary.txt
    │                                                  SUMMARY_REPORT.txt
    │                                                                 │
    ├── 07.ai_curator.smk（ai: true）───────────────┤
    │    ai_annotation_curator ──► 04.ai/{sample}_ai_report.md 等     │
    │                                                                 │
    ├── 08.deliver.smk ─────────────────────────────┤
    │    delivery ──► {data_deliver}/delivery_manifest.json/.md5      │
    │                 {data_deliver}/delivery_details.log             │
    └── 09.Report.smk ──────────────────────────────┘
         generate_project_summary ──► project_summary.json
```

### 各步骤说明

| 层 | 规则文件 | 主要 rule | 说明 |
|----|---------|-----------|------|
| 通用层 | 01.common.smk | —（输入解析辅助函数） | 无业务 rule |
| 通用层 | 02.input_md5.smk | input_md5_check | 输入 MD5 硬性门控，产出 `01.qc/md5_check.tsv` |
| 组学层 | 03.eggnog.smk | eggnog_mapper / eggnog_processor | eggnog-mapper 注释 + 质量过滤与可信度评估 |
| 组学层 | 04.kofamscan.smk | kofamscan / kofamscan_processor | KofamScan KO 注释 + 可信度评估 |
| 组学层 | 05.integrate.smk | integrate_annotations | 双工具横向整合与冲突裁决 |
| 组学层 | 06.merge.smk | merge_eggnog_results / merge_kofam_results / compare_kegg_annotations / annotation_summary / merge_summary_report | 多样本合并、KEGG KO 一致性比对与汇总 |
| 组学层 | 07.ai_curator.smk | ai_annotation_curator / ai_multi_sample_summary | AI 逐蛋白可靠性评估（可选） |
| 收尾层 | 08.deliver.smk | delivery | 交付 manifest（copy 模式） |
| 收尾层 | 09.Report.smk | generate_project_summary | `project_summary.json` |

> 日志与基准：`logs/`、`benchmarks/` 目录编号与 rule 文件号一致（如 `logs/03.eggnog/`、`logs/04.kofam/`）。

---

## 结果解读

### 输出文件结构

```
01.qc/                             # 输入校验
└── md5_check.tsv                  # 输入 MD5 校验结果（门控文件）⭐

01.eggnog/                         # eggnog-mapper 结果目录
├── {sample}.emapper.annotations   # eggnog 原始输出
├── {sample}.emapper.hits          # 比对详情
├── {sample}.emapper.seed_orthologs
├── {sample}_eggnog.tsv            # 处理后的 eggnog 结果 ⭐
├── {sample}_eggnog_highconf.tsv   # 高可信度子集 ⭐
└── {sample}_eggnog_report.txt     # 处理报告

02.kofam/                          # KofamScan 结果目录
├── {sample}_kofam_detail.txt      # KofamScan 原始输出
├── {sample}_kofam_raw.tsv         # mapper 格式原始输出
├── {sample}_kofam.tsv             # 处理后的 Kofam 结果
├── {sample}_kofam_highconf.tsv    # 高可信度子集
└── {sample}_kofam_report.txt      # 处理报告

03.merge/                          # 整合与合并结果目录
├── {sample}_integrated.tsv        # 单样本整合结果
├── {sample}_integrated_report.txt # 整合评分报告
├── {sample}_summary.txt           # 单样本摘要报告
├── eggnog_all_samples.tsv         # eggnog 多样本合并 ⭐⭐
├── eggnog_highconf.tsv            # eggnog 高可信度合并
├── kofam_all_samples.tsv          # kofam 多样本合并
├── kofam_highconf.tsv             # kofam 高可信度合并
├── kegg_consistency.tsv           # 双工具 KO 一致性逐蛋白比对 ⭐
├── kegg_consistency_stats.txt     # 一致性统计（一致/冲突/一致率）
└── SUMMARY_REPORT.txt             # 整体汇总报告

04.ai/                             # AI 分析结果目录（ai: true 时）
├── {sample}_ai_report.md          # AI 逐蛋白评估报告（Markdown）
├── {sample}_ai_analysis.json      # 结构化评估数据（JSON）
├── {sample}_ai_analysis.tsv       # 评估结果 TSV
├── {sample}_ai_analysis.csv       # 评估结果 CSV
└── AI_MULTI_SAMPLE_SUMMARY.md     # 多样本 AI 汇总

{data_deliver}/                    # 交付目录（deliver 模块）
├── delivery_manifest.json         # 交付文件清单（来源、大小、MD5、动作）
├── delivery_manifest.md5          # 各交付文件 MD5 列表
└── delivery_details.log           # 逐文件交付日志

project_summary.json               # 项目级摘要（report 模块）
```

### 结果文件格式

#### 1. `{sample}_eggnog.tsv`

主结果文件，包含完整的注释信息和可信度评估：

| 列名 | 说明 | 示例 |
|------|------|------|
| query | 查询序列 ID | gene_1 |
| seed_ortholog | 最佳匹配的种子同源基因 | 71139.XP_010029570.1 |
| evalue | E-value（越小越好）| 1.58e-168 |
| score | Bit-score（越大越好）| 485.0 |
| eggnog_ogs | eggNOG 直系同源组 | COG0679@1\|root,... |
| cog_category | COG 功能分类 | S |
| description | 功能描述 | Transporter |
| kegg_ko | KEGG KO 编号 | ko:K07088 |
| kegg_pathway | KEGG 通路 | ko03030,map03030 |
| gos | GO 注释 | GO:0003674,GO:0005215 |
| ec | EC 编号 | 1.8.4.12 |
| **confidence_level** | 可信度等级 | High/Medium/Low |
| **confidence_score** | 可信度分数 (0-100) | 95 |
| **confidence_reason** | 可信度说明 | High quality annotation |

#### 2. `{sample}_eggnog_highconf.tsv`

高可信度子集，只包含 confidence_level = "High" 的记录，格式同上。

#### 3. `03.merge/eggnog_all_samples.tsv`

多样本合并结果，**新增 sample 列**标识样本来源：

| sample | query | evalue | score | kegg_ko | confidence_level |
|--------|-------|--------|-------|---------|------------------|
| sample1 | gene1 | 1e-100 | 200 | ko:K00001 | High |
| sample1 | gene2 | 1e-50 | 150 | ko:K00002 | Medium |
| sample2 | gene1 | 1e-120 | 250 | ko:K00001 | High |

#### 4. `03.merge/{sample}_integrated.tsv`

整合评分结果，同时包含 eggNOG 和 KofamScan 的字段，以及综合评分：

| 列名 | 说明 |
|------|------|
| query | 蛋白 ID |
| integrated_ko | 最终选定的 KO |
| ko_agreement | agree / conflict / single_source |
| integrated_score | 综合评分 (0-100) |
| integrated_level | High / Medium / Low |
| eggnog_kegg_ko | eggNOG 的 KO |
| kofam_ko | KofamScan 的 KO |
| ... | 其余 eggnog + kofam 原始字段 |

#### 5. `03.merge/kegg_consistency.tsv`

双工具 KO 一致性逐蛋白比对：按 `(sample, query)` 对齐两个软件，去掉 `ko:` 前缀后比较 KO 集合。有交集记 `一致`，均有 KO 但无交集记 `冲突`。下游严格集合取 `status=一致` 且双方均为高置信的记录，冲突记录保留供人工复核。

### 统计报告解读

#### 处理报告示例 (`*_report.txt`)

```
EggNOG Annotation Processing Report
======================================================================

Parameters:
  E-value threshold: 1e-05
  Bit-score threshold: 60
  Mode: Standard
  Min confidence: High

Statistics:
  Total records: 99          ← 原始注释数
  Passed filter: 63 (63.6%)  ← 通过质量过滤
  Filtered out: 36 (36.4%)   ← 被过滤掉

Confidence Distribution:
  High: 92 (92.9%)           ← 高可信度 (推荐)
  Medium: 7 (7.1%)           ← 中等可信度
  Low: 0 (0.0%)              ← 低可信度

Annotation Coverage:
  With KEGG: 64 (64.6%)      ← 有 KEGG 注释
  With GO: 60 (60.6%)        ← 有 GO 注释
  With both KEGG and GO: 43 (43.4%)  ← 同时有两者
```

### 可信度评分标准

详见 `docs/filtering_standards.md`。简要如下：

**eggnog_processor**（0-100分）
- E-value 评分（0-40分）
- Bit-score 评分（0-30分）
- 注释完整性评分（0-30分，基于 GO/KO/EC/Pfam/CAZy）

**kofamscan_processor**（40-95分）
- High：通过阈值（`*`）且 score ≥ threshold
- Medium：未过阈值但 score > 100 或 evalue < 1e-20
- Low：score < 60 或 evalue > 1e-5

| 等级 | 总分范围 | 说明 | 建议 |
|------|----------|------|------|
| **High** | 80-100 | 高质量注释 | 可放心使用 |
| **Medium** | 50-79 | 中等质量 | 建议复核关键结果 |
| **Low** | 0-49 | 低质量 | 建议谨慎使用或丢弃 |

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

---

## AI 注释分析功能

AnnoFlow 支持 AI 驱动的**逐蛋白可靠性评估**（模块开关 `ai: true`，默认关闭），而非仅样本级汇总统计。

### 功能特点

- **逐蛋白可靠性评估**: 对每条蛋白分别评估 eggNOG 和 KofamScan 的可靠性
- **物种合理性判断**: 结合 `taxonomy` 参数，判断注释功能对该物种是否合理
- **Tax_scope 精确度检查**: 评估 eggNOG `tax_scope` 与物种分类的匹配层级
- **KofamScan 阈值比值解读**: 结合 KO 类型（管家基因 vs 稀有基因）判断 ratio 可信度
- **工具一致性检测**: 自动标记 eggNOG 与 KofamScan 的 KO 冲突
- **分层筛选降本**: 高置信/低质量两端由规则直接判定，仅模糊区域送 AI
- **Token 消耗追踪**: 自动统计 prompt/completion/total tokens，便于成本控制

### 支持的 AI 提供商

| 提供商 | 模型示例 | 特点 |
|--------|---------|------|
| **Ollama** (默认) | llama3.2, mistral | 本地运行，无需联网，免费 |
| **OpenAI** | gpt-4, gpt-3.5-turbo | 云端 API，性能强 |
| **Claude** | claude-3-sonnet | 云端 API，擅长长文本 |

### 快速开始

#### 1. 使用本地 Ollama（推荐）

```bash
# 安装 Ollama
curl -fsSL https://ollama.com/install.sh | sh

# 下载模型（以 llama3.2 为例，4GB 左右）
ollama pull llama3.2

# 确认服务运行
curl http://localhost:11434/api/tags
```

#### 2. 在 analysisyaml 中启用 AI

```yaml
# project.yaml
ai: true                 # 模块开关（替代旧版的 enabled 开关）
ai_config:
  provider: "ollama"
  model: "llama3.2"
  taxonomy: "Bacteria;Firmicutes;Bacillales"  # 你的物种分类
  max_proteins: 50                              # 仅对模糊区域最多评估 50 个蛋白
  # api_base: "http://localhost:11434"         # 可选：自定义端点
```

#### 3. 运行分析

```bash
# 运行完整流程（包含 AI 分析）
snakemake -s /path/to/AnnoFlow/snakefile --cores 8 --use-conda --conda-frontend mamba \
  --config analysisyaml=/path/to/project.yaml

# 或仅运行 AI 分析（已有注释结果时）
snakemake -s /path/to/AnnoFlow/snakefile --cores 8 --use-conda --conda-frontend mamba \
  --config analysisyaml=/path/to/project.yaml ai_analysis
```

### 输出结果

```
04.ai/
├── {sample}_ai_report.md          # AI 逐蛋白评估报告（Markdown）⭐
├── {sample}_ai_analysis.json      # 结构化评估数据（JSON）⭐
└── AI_MULTI_SAMPLE_SUMMARY.md     # 多样本汇总（多样本时）
```

#### AI 报告内容示例

```markdown
# AI 注释分析报告（逐蛋白评估）

## 处理策略与 Token 消耗
- 规则直接判定: 230 个蛋白（不消耗 token）
- AI 实际评估: 50 个蛋白
- Total tokens: 184,320

## 整体质量汇总
- High confidence: 42 (14.0%)
- Medium confidence: 28 (9.3%)
- Low confidence: 8 (2.7%)
- Cross-tool conflicts: 5

## 潜在问题蛋白（Top 20）
- `gene_23` | Overall: Low | Action: Reject | Source: AI | Flags: Eukaryota tax_scope in bacteria
...
```

### 分层筛选策略说明

为控制 Token 成本，`ai_curator.py` 默认开启**分层筛选**（可将 `ai_config.no_auto_filter` 设为 `true` 关闭）：

| 分类 | 判定标准 | 处理方式 | Token 消耗 |
|------|----------|----------|-----------|
| **高置信** | `e-value < 1e-10` **且** `Kofam ratio > 1.5` | 规则直接 `Accept` | 0 |
| **低质量** | `e-value > 1e-3` **或** `Kofam ratio < 0.5` | 规则直接 `Reject` | 0 |
| **模糊区域** | 其余蛋白 | 送 AI 评估 | 有 |

这意味着对于一个 3000 蛋白的基因组，可能只有 300-600 个蛋白进入模糊区域，再按 `max_proteins` 限制后，实际 API 调用可能只有几十个，大幅降低成本。

---

## 安全指南 🔒

### API 密钥安全最佳实践

**⚠️  绝对不要直接在配置文件中写入真实 API key！**

#### 安全风险

| 方式 | 风险等级 | 说明 |
|------|---------|------|
| 明文写在 yaml 配置 | 🔴 极高 | 可能被提交到 Git，泄露密钥 |
| 命令行参数传递 | 🟠 高 | 会被记录在 shell 历史和进程列表 |
| 环境变量（✅ 推荐） | 🟢 低 | 只在内存中存在，不会持久化到文件 |

#### ✅ 推荐做法：使用环境变量

##### 步骤 1：设置环境变量（在运行前）

```bash
# 方式 1：当前 shell 会话（推荐用于测试）
export AI_API_KEY="sk-your-actual-api-key"

# 方式 2：写入 ~/.bashrc 或 ~/.zshrc（长期有效）
echo 'export AI_API_KEY="sk-your-actual-api-key"' >> ~/.bashrc
source ~/.bashrc
```

##### 步骤 2：在 ai_config 中只写变量名

```yaml
ai: true
ai_config:
  provider: "openai"
  model: "glm-4.7"
  api_key: "AI_API_KEY"      # ← ✅ 只写变量名，不写真实 key
  api_base: "https://dashscope.aliyuncs.com/compatible-mode/v1"
```

##### 步骤 3：运行分析

```bash
snakemake -s /path/to/AnnoFlow/snakefile --cores 8 --use-conda --conda-frontend mamba \
  --config analysisyaml=/path/to/project.yaml
```

### 🔐 安全机制说明

本流程已实施以下安全措施：

1. **配置占位检测**：`api_key` 约定为全大写环境变量名格式，脚本从环境变量读取真实值；真实 key 永不入库
2. **命令行保护**：即使通过命令行传入 key，也会立即转移到环境变量，避免在 `ps` 进程列表中暴露
3. **日志脱敏**：API key 不会出现在任何日志文件中，日志只显示 `长度: 32` 而非真实内容
4. **Git 保护**：`.gitignore` 已包含 `.env`、`*.log`、运行产物等，防止意外提交敏感信息
5. **监控配置同策略**：`monitor_config.yaml` 的 token / signing key 一律用 `${ENV_VAR}` 引用

### 使用不同云平台

#### 阿里云百炼 (DashScope)

```bash
export DASHSCOPE_API_KEY="sk-your-dashscope-key"
```

```yaml
ai: true
ai_config:
  provider: "openai"  # 阿里云使用兼容模式
  model: "glm-4.7"
  api_key: "DASHSCOPE_API_KEY"
  api_base: "https://dashscope.aliyuncs.com/compatible-mode/v1"
```

#### OpenAI 官方

```bash
export OPENAI_API_KEY="sk-your-openai-key"
```

```yaml
ai: true
ai_config:
  provider: "openai"
  model: "gpt-4"
  api_key: "OPENAI_API_KEY"
  # api_base 默认为 https://api.openai.com/v1
```

#### 本地 Ollama（最安全，无需 API key）

```bash
# 无需设置 API key
ollama serve
```

```yaml
ai: true
ai_config:
  provider: "ollama"
  model: "llama3.2"
  # api_key 留空
  # api_base: "http://localhost:11434"
```

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

迁移步骤：准备数据库目录（`dataset/eggnog-mapper` + `dataset/kegg_<date>_ko_dataset`）→ 将旧样本列表改写为 `samples.csv` → 按 `examples/analysisyaml.example.yaml` 填写七项必填配置 → dry-run 验证 → 正式运行。

---

## 常见问题

### Q1: 首次运行很慢？

A: 首次运行时需要下载并创建 Conda 环境，可能需要 10-30 分钟。环境创建后会缓存，后续运行会很快。

### Q2: eggnog-mapper 找不到数据库？

A: 确认 analysisyaml 中的 `reference_path` 指向参考目录根，且其下存在 `dataset/eggnog-mapper/`（含 `eggnog.db`）与 `dataset/kegg_<date>_ko_dataset/`。参考路径在启动时 fail-fast 检查，先跑 dry-run（`-n`）即可暴露路径错误。

### Q3: 如何只处理已有结果，不重新跑注释？

A: 已有 `01.eggnog/*.emapper.annotations` 后，可直接运行后续处理步骤：

```bash
snakemake -s /path/to/AnnoFlow/snakefile --cores 4 --use-conda --conda-frontend mamba \
  --config analysisyaml=/path/to/project.yaml annotate
```

### Q4: 如何调整过滤严格程度？

A: 在 analysisyaml 中覆盖 `run_parameter.yaml` 的阈值键：

```yaml
# 严格模式
evalue_threshold: 1.0e-10
bitscore_threshold: 80
min_confidence: "High"

# 宽松模式
evalue_threshold: 1.0e-5
bitscore_threshold: 40
min_confidence: "Medium"
```

### Q5: 多样本如何合并分析？

A: 在 `samples.csv` 中每行一个样本，运行后自动生成 `03.merge/` 下的合并结果与 `SUMMARY_REPORT.txt`。

### Q6: AI 分析为什么没有评估所有蛋白？

A: 这是正常的成本控制设计。默认开启分层筛选：高置信和低质量蛋白由规则直接判定，只有模糊区域才送 AI。如需扩大评估量，在 analysisyaml 的 `ai_config` 中调大 `max_proteins`；全量评估则设 `no_auto_filter: true`（⚠️ 会消耗大量 Token）。

### Q7: 输入文件名带复合扩展名（如 `.fa.TD2.1k.pep`）如何配置？

A: 输入解析已支持复合扩展名。样本表 `sample` 列写基础名即可：

```csv
sample,sample_name
rnabloom_transcript_LongOrfs,RNA-Bloom ORFs
```

系统会自动匹配 `rnabloom_transcript_LongOrfs.fa.TD2.1k.pep`。

### Q8: 为什么 `--config ai=false` 关不掉 AI 模块？

A: 命令行 `--config` 的布尔值会被解析为字符串，非空字符串恒为真。关闭模块请在 analysisyaml 中写 `ai: false`（其余模块开关同理）。

---

## 过滤阈值参考

| 质量标准 | 标准模式 | 严格模式 | 说明 |
|----------|----------|----------|------|
| E-value | ≤ 1e-5 | ≤ 1e-10 | 控制假阳性 |
| Bit-score | ≥ 60 | ≥ 80 | 比对得分 |
| Percentage identity | ≥ 40-50% | ≥ 70% | 序列同一性 |
| Query coverage | ≥ 20% | ≥ 30% | 查询序列覆盖率 |
| Subject coverage | ≥ 30% | ≥ 50% | 参考序列覆盖率 |

---

## 文档与参考

- **过滤标准详解**: 见 `docs/filtering_standards.md`
- **项目级配置示例**: 见 `examples/analysisyaml.example.yaml`
- **Snakemake 官方文档**: https://snakemake.readthedocs.io/
- **eggnog-mapper 文档**: https://github.com/eggnogdb/eggnog-mapper
- **KofamScan 文档**: https://www.genome.jp/tools/kofamkoala/

---

## 依赖

- Python 3.12（`env/py3.12.yaml`：pandas, loguru, rich, requests 等）
- eggnog-mapper 2.1.13（`env/eggnog-mapper.yaml`）
- KofamScan 1.3.0（`env/kofamscan.yaml`）
- Snakemake 9.9.0+
- Conda/Mamba

---

## 引用

如果使用本流程，请引用：

1. eggNOG-mapper v2: [https://doi.org/10.1093/molbev/msab293](https://doi.org/10.1093/molbev/msab293)
2. eggNOG 5.0: [https://doi.org/10.1093/nar/gky1085](https://doi.org/10.1093/nar/gky1085)
3. KofamScan: [https://doi.org/10.1093/bioinformatics/btz859](https://doi.org/10.1093/bioinformatics/btz859)
