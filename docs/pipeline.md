# AnnoFlow 分析流程与结果说明

本文档说明 AnnoFlow 的完整分析流程、各步骤的输入输出，以及如何解读结果文件。

- 配置与运行命令见 [usage.md](usage.md)
- 过滤与可信度评分的完整标准见 [filtering_standards.md](filtering_standards.md)

---

## 流程图

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
    │    export_annotation_sets ──► 03.merge/go_annotations.tsv 等    │
    │    export_rnaflow_annotation ──► 03.merge/rnaflow_annotation.tsv│
    │                                  03.merge/kegg_pathway_names.tsv│
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

## 各步骤说明

| 层 | 规则文件 | 主要 rule | 说明 |
|----|---------|-----------|------|
| 通用层 | 01.common.smk | —（输入解析辅助函数） | 无业务 rule |
| 通用层 | 02.input_md5.smk | input_md5_check | 输入 MD5 硬性门控，产出 `01.qc/md5_check.tsv` |
| 组学层 | 03.eggnog.smk | eggnog_mapper / eggnog_processor | eggnog-mapper 注释 + 质量过滤与可信度评估 |
| 组学层 | 04.kofamscan.smk | kofamscan / kofamscan_processor | KofamScan KO 注释 + 可信度评估 |
| 组学层 | 05.integrate.smk | integrate_annotations | 双工具横向整合与冲突裁决 |
| 组学层 | 06.merge.smk | merge_eggnog_results / merge_kofam_results / compare_kegg_annotations / export_annotation_sets / export_rnaflow_annotation / annotation_summary / merge_summary_report | 多样本合并、KEGG KO 一致性比对、GO/KO 导出、RNAFlow 衔接导出与汇总 |
| 组学层 | 07.ai_curator.smk | ai_annotation_curator / ai_multi_sample_summary | AI 逐蛋白可靠性评估（可选） |
| 收尾层 | 08.deliver.smk | delivery | 交付 manifest（copy 模式） |
| 收尾层 | 09.Report.smk | generate_project_summary | `project_summary.json` |

> 日志与基准：`logs/`、`benchmarks/` 目录编号与 rule 文件号一致（如 `logs/03.eggnog/`、`logs/04.kofam/`）。

## 输入 MD5 硬性门控（rules/02.input_md5.smk）

所有样本输入文件必须完成 MD5 校验才生成 `01.qc/md5_check.tsv`；下游 `eggnog_mapper` / `kofamscan` 显式依赖该门控文件，校验不过根本不会启动比对。行为规则：

- `input_dir` 下存在 `md5.txt`（格式：`<md5><空格><文件名>`）→ 逐文件比对
- 无 `md5.txt` → 计算并记录基线，标记 PASS（SRA 兼容原则）
- 任一 FAIL 或输入文件缺失 → 立即非零退出，流程中止

---

## 输出文件结构

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
├── go_annotations.tsv             # 原始 eggNOG GO 注释，每个 sample+query 一行
├── go_annotations_highconf.tsv    # GO 高可信版本
├── gene2go.tsv                    # GO 长表，每个 sample+query+GO 一行
├── gene2go_highconf.tsv           # GO 高可信长表
├── go_annotation_stats.txt        # GO 去重计数
├── kegg_shared.tsv                # 两方法共有 KO，每个 sample+query 一行
├── kegg_shared_highconf.tsv       # 双方高可信共有 KO
├── gene2ko_shared.tsv             # 共有 KO 长表，每个 sample+query+KO 一行
├── gene2ko_shared_highconf.tsv    # 双方高可信共有 KO 长表
├── kegg_shared_stats.txt          # 共有 KO 去重计数
├── rnaflow_annotation.tsv         # RNAFlow 直接可用的 GO & KEGG 注释表 ⭐
├── kegg_pathway_names.tsv         # ko##### 通路 ID -> KEGG 通路名映射
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

## 结果文件格式

### 1. `{sample}_eggnog.tsv`

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

### 2. `{sample}_eggnog_highconf.tsv`

高可信度子集，只包含 confidence_level = "High" 的记录，格式同上。

### 3. `03.merge/eggnog_all_samples.tsv`

多样本合并结果，**新增 sample 列**标识样本来源：

| sample | query | evalue | score | kegg_ko | confidence_level |
|--------|-------|--------|-------|---------|------------------|
| sample1 | gene1 | 1e-100 | 200 | ko:K00001 | High |
| sample1 | gene2 | 1e-50 | 150 | ko:K00002 | Medium |
| sample2 | gene1 | 1e-120 | 250 | ko:K00001 | High |

### 4. `03.merge/{sample}_integrated.tsv`

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

### 5. `03.merge/kegg_consistency.tsv`

双工具 KO 一致性逐蛋白比对：按 `(sample, query)` 对齐两个软件，去掉 `ko:` 前缀后比较 KO 集合。有交集记 `一致`，均有 KO 但无交集记 `冲突`。下游需要精确的共有 KO 时使用 `kegg_shared.tsv` / `gene2ko_shared.tsv`（高可信对应 `_highconf`），不要把 `status=一致` 当成整个 KO 集合相同；冲突记录保留供人工复核。

### 6. 独立 GO 与共有 KEGG KO 导出

`go_annotations.tsv` 与 `go_annotations_highconf.tsv` 每个 `(sample, query)` 一行，含 `go_terms`（分号分隔、去重排序）及 `source`。`gene2go.tsv` 和 `_highconf.tsv` 每个 `(sample, query, go_term)` 一行，另含来源、`evalue`、`bitscore` 和该条 eggNOG 原始记录的 `confidence`；重复 query 的 GO 取并集，不同样本绝不合并。这里的 `query` 是**输入蛋白 ID 原样**，`gene2go` 不负责转为基因 ID，也不删转录本后缀。GO 完整版本直接读取原始 `.emapper.annotations` 的有效 GO，**不受 `require_kegg`、E-value 或 High 条件筛选**；高可信版本复用 eggNOG 现有评分规则，要求 E-value ≤ 配置阈值、Bit-score ≥ 配置阈值且 `confidence_level=High`，但不要求 KEGG。统计中的 `go_only_no_kegg_proteins` 以原始 eggNOG KO 字段为准。这些是 **GO 注释结果，不是 GO 富集分析**。

`kegg_shared.tsv` 与 `_highconf.tsv` 每个 `(sample, query)` 一行，`shared_ko` 是**相同蛋白的两工具 KO 集合交集**（分号分隔）；`eggnog_ko`、`kofam_ko` 给出双方各自的完整已处理集合。`gene2ko_shared.tsv` 与 `_highconf.tsv` 每个 `(sample, query, shared_ko)` 一行，并保留双方 `confidence`、eggNOG `evalue`/`score`（`eggnog_bitscore`）、KofamScan `score`/`kofam_threshold`（原表不含 ratio，故不虚构）。KO 规范为 `Kxxxxx`；不是通路编号，也不是最终 `integrated_ko`。仅 eggNOG 或仅 KofamScan 给出 KO、或者两者 KO 无交集的蛋白不进入共有表；原 `kegg_consistency.tsv` 仍保留单来源与冲突信息；其中 `一致` 指**存在交集**，并不表示 KO 集合完全相等。

普通共有版本来自两个工具**已处理的主表**：eggNOG 主表已经过 E-value、Bit-score、`min_confidence` 及可配置的 `require_kegg`/`require_go` 过滤；KofamScan 主表选每个蛋白最佳 KO，但目前**不按 `min_confidence` 过滤**（该处理器只计算可信度和单独写 High 子集）。高可信共有严格对两工具的 `*_highconf.tsv` 按**同一 KO**再次取交集；上游可信度是 eggNOG 注释记录和 KofamScan 最佳 hit 级别，不是逐 KO 独立验证。这些是双工具共同支持的**注释，不是实验验证结果**。如果主表因 `require_kegg`/其他条件缺少某蛋白，普通共有表不会用原始注释补回。两种导出可从已有原始 eggNOG 文件与两工具已处理表重新生成，不会改写既有注释或 GO 文件。

`go_annotation_stats.txt` / `kegg_shared_stats.txt` 的蛋白数均按 `(sample, query)` 去重，蛋白–term 对按 `(sample, query, term)` 去重；它们的分母为相应原始 GO 或已处理 KO 表中有注释的蛋白，不代表输入 FASTA 总数。

### 7. RNAFlow 衔接导出（`rnaflow_annotation.tsv` / `kegg_pathway_names.tsv`）

`rnaflow_annotation.tsv` 由 `export_rnaflow_annotation` 规则从 `eggnog_all_samples.tsv` 导出，是 **RNAFlow 富集分析可直接消费的注释表**（全量置信度，含 `confidence_level` 供下游按需过滤；`query` 保留原始转录本 ID，基因 ID 归一由 RNAFlow 侧处理）：

| 列名 | 说明 | 示例 |
|------|------|------|
| query | 查询序列 ID（RNAFlow 要求列） | Chr1_gene_70800_mRNA |
| description | 功能描述 | SNO glutamine amidotransferase family |
| ec | EC 编号 | 4.3.3.6 |
| gos | GO 注释（RNAFlow 要求列） | GO:0003674,GO:0003824 |
| kegg_ko | KEGG KO 编号 | ko:K08681 |
| kegg_pathway | KEGG 通路 ID（RNAFlow 要求列） | ko00750,map00750 |
| confidence_level | 可信度等级 | High |
| confidence_score | 可信度分数 (0-100) | 100 |

`kegg_pathway_names.tsv` 是 `ko##### 通路 ID -> 通路名` 两列映射。名称解析顺序：**参考库缓存 → KEGG REST（ko 列表为主，map 列表补充）→ 内置已退役通路历史名**（依据 [KEGG 更新记录](https://www.genome.jp/kegg/docs/upd_map.html)）；全部不可用时仍生成文件但映射为空并告警。观测到但没有现行名称的 ID（已退役或数据库过旧）会在日志中列出。获取与部署细节见 [database_preparation.md](database_preparation.md)。

在 RNAFlow 中使用。**推荐**先把两个文件复制到 RNAFlow 参考库中该基因组的目录（与 index/GTF 等参考资产放在一起，避免依赖会被清理的项目目录），再写相对路径：

```bash
cp 03.merge/rnaflow_annotation.tsv \
   <RNAFlow_reference>/<genome_version>/<genome_version>_rnaflow_annotation.tsv
cp 03.merge/kegg_pathway_names.tsv \
   <RNAFlow_reference>/<genome_version>/<genome_version>_kegg_pathway_names.tsv
```

```yaml
# RNAFlow config/reference.yaml 对应基因组条目
annotation_table: <genome_version>/<genome_version>_rnaflow_annotation.tsv
annotation_format: eggnog
kegg_pathway_names: <genome_version>/<genome_version>_kegg_pathway_names.tsv
```

之后 RNAFlow 的富集结果（`07.Enrichments/*.csv`）的 Description 列即为真实通路名而非 `ko#####` ID。

## 统计报告解读

### 处理报告示例（`*_report.txt`）

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

完整评分规则见 [filtering_standards.md](filtering_standards.md)。简要如下：

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