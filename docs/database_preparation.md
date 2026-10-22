# AnnoFlow 参考数据库准备指南

AnnoFlow 依赖三个参考数据库组件，统一部署在 `reference_path` 下，由 `config/reference.yaml` 的路径键指向：

```
<reference_path>/                      # 如 /data/jzhang/reference/AnnoFlow
└── dataset/
    ├── eggnog-mapper/                 # ① eggNOG 数据库（eggnog.db 等）
    ├── kegg_<date>_ko_dataset/        # ② KOfam 数据库
    │   ├── ko_list                    #    KO 阈值列表
    │   └── profiles/                  #    HMM profiles
    └── kegg_pathway_names.tsv         # ③ KEGG 通路名映射（首次运行自动生成，离线复用）
```

在 analysisyaml 中通过 `reference_path`（绝对路径）指定根目录；`eggnog_data_dir` / `kofam_ko_list` / `kofam_profiles` 相对 `reference_path` 解析（写成绝对路径则直接使用）。参考路径在启动时 fail-fast 检查，先跑 dry-run（`-n`）即可暴露路径错误。

> **注意**：`ko_list` 只含 KO（`K#####`）的阈值与功能定义，**不含通路名**；`eggnog.db` 也只有通路 ID。ko 通路名由 `export_rnaflow_annotation` 规则在首次运行时从 KEGG REST 拉取并写入 `kegg_pathway_names.tsv` 缓存（见第 ③ 节）。

各注释工具的原理与完整手动用法教程见 [kegg-annotation.md](kegg-annotation.md)。

---

## ① eggNOG 数据库（dataset/eggnog-mapper/）

### 方式一：官方脚本自动下载（推荐）

```bash
download_eggnog_data.py -y -F -M -P --data_dir <reference_path>/dataset/eggnog-mapper/
```

- `-F`：新基因家族库（novel_fams，eggNOG 6）
- `-M`：MMseqs2 库
- `-P`：Pfam 库

### 方式二：手动下载

```bash
# 核心库 (eggnog.db)
wget http://eggnog5.embl.de/download/emapperdb-5.0.2/eggnog.db.gz
# 物种分类树库
wget http://eggnog5.embl.de/download/emapperdb-5.0.2/eggnog.taxa.tar.gz
# 全物种 Diamond 索引
wget http://eggnog5.embl.de/download/emapperdb-5.0.2/eggnog_proteins.dmnd.gz
# 新基因家族库 (对应 -F)
wget http://eggnog6.embl.de/download/novel_fams-1.0.1/novel_fams.dmnd.gz
wget http://eggnog6.embl.de/download/novel_fams-1.0.1/novel_fams.pkl.gz
# MMseqs2 和 Pfam 库 (对应 -M 和 -P)
wget http://eggnog5.embl.de/download/emapperdb-5.0.2/mmseqs.tar.gz
wget http://eggnog5.embl.de/download/emapperdb-5.0.2/pfam.tar.gz
```

下载完成后的目录结构：

```
dataset/eggnog-mapper/
├── eggnog.db                      # 解压后的 SQLite 数据库（约 3.5G）
├── eggnog.taxa/                   # 解压后的分类树目录
├── eggnog_proteins.dmnd.gz        # ❗保持压缩（约 15G）
├── novel_fams.dmnd.gz             # ❗保持压缩（约 2G）
├── novel_fams.pkl.gz              # ❗保持压缩（约 500M）
├── mmseqs/                        # 解压后的 MMseqs2 索引（可选）
└── pfam/                          # 解压后的 Pfam 目录（可选）
```

> `.dmnd.gz` / `.pkl.gz` 是 emapper 按需流式解压读取的，**不要提前解压**（`eggnog.db` 与 `eggnog.taxa` 才需要解压）。

---

## ② KOfam 数据库（dataset/kegg_\<date\>_ko_dataset/）

从 KEGG 官方 FTP 下载指定日期版本：

```bash
# 2026-02-01 版本
wget https://www.genome.jp/ftp/db/kofam/archives/2026-02-01/ko_list.gz
wget https://www.genome.jp/ftp/db/kofam/archives/2026-02-01/profiles.tar.gz

# 解压到参考目录
mkdir -p <reference_path>/dataset/kegg_2026-02-01_ko_dataset
gunzip ko_list.gz -c > <reference_path>/dataset/kegg_2026-02-01_ko_dataset/ko_list
tar -xzf profiles.tar.gz -C <reference_path>/dataset/kegg_2026-02-01_ko_dataset/
```

下载后更新 `config/reference.yaml`（或 analysisyaml）中的 `kofam_ko_list` / `kofam_profiles` 指向新版本目录。

> KofamScan 工具本身的 `config.yaml`（profile / ko_list / cpu 等）由流程的 conda 环境与规则参数接管，无需手动配置。

---

## ③ kegg_pathway_names.tsv（KEGG 通路名映射）

### 文件是什么

两列 TSV：KEGG 通路 ID → 通路名称，无表头：

```
ko00010    Glycolysis / Gluconeogenesis
ko00020    Citrate cycle (TCA cycle)
...
```

它**不是需要下载的数据库文件**，而是运行 AnnoFlow 时由 `scripts/export_rnaflow_annotation.py` 自动从 KEGG REST API 抓取生成、并缓存在参考库目录的映射表；首次生成后完全离线复用，另内置 5 条 KEGG 已退役通路的历史名称兜底。

### 获取方式（三种，按优先级）

#### 方式一：跑 AnnoFlow 自动生成（推荐，无需操作）

`export_rnaflow_annotation` 规则执行时，脚本按 **缓存 → KEGG REST → 退役表** 的顺序解析（`export_rnaflow_annotation.py` 的 `load_pathway_names()`）：

1. 缓存存在且非空 → 直接使用，完全离线
2. 否则请求 KEGG REST 两个接口，并自动写回缓存（以后离线可用）：
   - `https://rest.kegg.jp/list/pathway/ko`（ko 级通路，主体）
   - `https://rest.kegg.jp/list/pathway`（map 级补充，`map#####` 转成 `ko#####`；有些通路只有 map 条目，如 ko01062）
3. 无论哪种来源，最后叠加 5 条已退役通路的历史名（`RETIRED_PATHWAYS`；这些 ID 被 KEGG 官方删除/合并，但旧版 eggNOG 仍可能注释到它们）

全部不可用时仍生成文件但映射为空并告警，不会导致流程失败。

#### 方式二：手动 curl 生成（提前准备数据库时）

```bash
# ko 级为主体，map 级补充，再追加退役通路
curl -s https://rest.kegg.jp/list/pathway/ko | sed 's/^path://' > kegg_pathway_names.tsv
curl -s https://rest.kegg.jp/list/pathway    | sed 's/^path:map/ko/' | \
  awk 'NR==FNR{seen[$1]=1; next} !seen[$1]' kegg_pathway_names.tsv - >> kegg_pathway_names.tsv
# 追加 5 条退役通路（从脚本 RETIRED_PATHWAYS 复制），最后按 ID 排序去重
```

#### 方式三：指定已有文件

`config/reference.yaml`（或 analysisyaml）中设置 `kegg_pathway_names` 可覆盖默认位置：

```yaml
kegg_pathway_names: /path/to/kegg_pathway_names.tsv   # 绝对路径，或相对 reference_path
```

### 默认存放位置

由 snakefile 自动推导：**KOfam `ko_list` 所在目录的上两级** + `kegg_pathway_names.tsv`，即 `dataset/` 根目录，与 `ko_list` 目录同级归档：

```
<reference_path>/dataset/
├── kegg_2026-02-01_ko_dataset/
│   └── ko_list                        ← KOfam 数据库（K##### 是 KO 编号，≠ 通路 ko#####）
├── eggnog-mapper/                     ← eggNOG 数据库
└── kegg_pathway_names.tsv             ← 本文件
```

---

## 部署与验证

1. 按 §①②③ 准备 `<reference_path>/dataset/` 目录
2. analysisyaml 中设置 `reference_path`（绝对路径）：

```yaml
reference_path: /data/jzhang/reference/AnnoFlow
```

3. dry-run 验证（fail-fast 检查会立即暴露路径错误）：

```bash
snakemake -s /path/to/AnnoFlow/snakefile -n \
  --config analysisyaml=/path/to/project.yaml
```