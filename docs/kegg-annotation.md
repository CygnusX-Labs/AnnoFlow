# kegg-annotation

## 目录

- [1 Introduce](#1-Introduce)
  - [1.1   kofam\_scan \&eggnog-mapper](#11---kofam_scan-eggnog-mapper)
- [2 Tutorial](#2-Tutorial)
  - [2.1 kegg download](#21-kegg-download)
  - [2.2 KofamScan](#22-KofamScan)
    - [2.2.1 KofamScan Download](#221-KofamScan-Download)
    - [KofamScan Annotation](#KofamScan-Annotation)
    - [KofamScan Result](#KofamScan-Result)
  - [2.3 eggnog-mapper](#23-eggnog-mapper)
    - [2.3.1 download eggnog-mapper dataset](#231-download-eggnog-mapper-dataset)
    - [2.3.2 KEGG Annotation by emapper.py](#232-KEGG-Annotation-by-emapperpy)
    - [2.3.3 Result](#233-Result)
- [3 Reference](#3-Reference)

***

***Author***\*\* : JZHANG\*\*​

***Date***\*\* : 2026-7-8\*\*​

***Version***\*\* : 1.0v\*\*​

***

## 1 Introduce

### 1.1   `kofam_scan` &`eggnog-mapper`

> 🧖在进行转录组或基因组的功能注释时，获取准确的 `KEGG` (`Kyoto Encyclopedia of Genes and Genomes`) 注释是连接基因序列与生物学代谢通路的核心环节。针对不同的研究物种和数据基础，本教程整合了三种主流的基因功能与 KEGG 注释获取策略：
>
> 1. **`KEGG REST API`**\*\* (直接获取官方注释)\*\* ​[^1]
>
>    对于在 `KEGG` 数据库中已经收录的参考物种（如拟南芥、番茄等模式或部分非模式物种），最直接、最准确的方式是通过 `KEGG`官方提供的 `REST API` 批量拉取数据。这种方式无需进行复杂的序列比对计算，能够零门槛获取官方最高置信度的基因、`KO` (`KEGG Orthology`) 以及 `Pathway` 映射网络。
> 2. **`KofamScan`**\*\* (基于 ****`HMM`**** 的高精度从头注释)\*\*[^2]
>
>    对于无参考基因组的非模式物种或全新组装的序列，`KofamScan` 提供了极具针对性的解决方案。这是一款基于 `KEGG` 官方直系同源系统和隐马尔可夫模型（`HMM`）的本地注释工具。通过预先下载 `KOfam` 数据库，它利用自适应阈值（`bit-score threshold`）为序列提供严谨的 `KO` 编号预测，是目前预测纯正 `KEGG` 通路最可靠的离线工具之一。
> 3. **`eggnog-mapper`**\*\* (基于直系同源群的综合快速注释)\*\* ​[^3]
>
>    `eggNOG-mapper` 是一款用于对大批量新序列进行快速、全景式功能注释的工具。它跨越了单一数据库的局限，利用 `eggNOG`数据库中预先计算好的直系同源群（`orthologous groups`）和系统发育树信息，通过细粒度的序列比对来推导（转移）功能信息。它不仅能高通量地输出 `KEGG` 注释，还能同时提供 `GO`、`COG`、`Pfam` 等多维度的功能特征。

***

## 2 Tutorial

### 2.1 kegg download

> 🤯\*\*`KEGG`****数据库可以通过****`REST API`****，可以直接用 ****`wget`****/****`curl`批量拉取特定物种的全部注释，不需要订阅\*\*​
>
> > \*\*NOTE \*\*: 当不知道自己要下载的物种的缩写是什么可以去 `https://www.genome.jp/kegg/tables/br08606.html`网页进行查询呀。
>
> 1. **物种所有基因列表** : 获取该物种在 `KEGG` 中收录的全部基因条目。
>    ```bash title="get <org>_gene.list"
>    # 从kegg数据库拉取
>    wget https://rest.kegg.jp/list/<org> -O <org>_gene.list
>    # 拟南芥下载示例
>    wget https://rest.kegg.jp/list/ath -O ath_gene.list
>    ```
>
>    > \*\*`ath_gene.list`\*\***文件格式：**
>    >
>    > ```text title="ath_gene.list"
>    > ath:AT1G01010    NAC domain containing protein 1 [KO:K12345]
>    > ath:AT1G01020    Protein of unknown function [KO:K67890]
>    > ...
>    > ```
>    >
> 2. **基因 ↔ 通路 映射（最关键）**: 建立基因与 KEGG Pathway 之间的映射关系，这是富集分析的核心输入。
>    ```bash title="get <org>_pathway.list"
>    # 从kegg数据库拉取
>    wget https://rest.kegg.jp/link/pathway/<org> -O <org>_pathway.list
>    # 拟南芥下载示例
>    wget https://rest.kegg.jp/link/pathway/ath -O ath_pathway.list
>    ```
>
>    > \*\*`ath_pathway.list`\*\***文件格式：**
>    >
>    > ```text title="ath_pathway.list"
>    > ath:AT1G01010    path:ath00010
>    > ath:AT1G01020    path:ath00190
>    > ...
>    > ```
>    >
> 3. **基因 ↔ KO (KEGG Orthology) 映射** : 建立基因与 KO 编号之间的映射，KO 是跨物种功能注释的核心桥梁。
>    ```bash title="get <org>_ko.list"
>    # 从kegg数据库拉取
>    wget https://rest.kegg.jp/link/ko/<org> -O <org>_ko.list
>    # 拟南芥下载示例
>    wget https://rest.kegg.jp/link/ko/ath -O ath_ko.list
>    ```
>
>    > \*\*`<org>_ko.list`\*\***文件格式：**
>    >
>    > ```text title="ath_ko.list"
>    > ath:AT1G01010    ko:K12345
>    > ath:AT1G01020    ko:K67890
>    > ...
>    > ```
>    >
> 4. **通路列表** : 获取该物种所有通路（Pathway）的 ID 与名称对照。
>    ```bash title="<org>_pathway_name.list"
>    # 从kegg数据库拉取
>    wget https://rest.kegg.jp/list/pathway/<org> -O <org>_pathway_name.list
>    # 拟南芥下载示例
>    wget https://rest.kegg.jp/list/pathway/ath -O ath_pathway_name.list
>
>    ```
>
>    > \*\*`ath_pathway_name.list`\*\***文件格式：**
>    >
>    > ```text title="ath_pathway_name.list"
>    > path:ath00010    Glycolysis / Gluconeogenesis [PATH:ath00010]
>    > path:ath00020    Citrate cycle (TCA cycle) [PATH:ath00020]
>    > ...
>    > ```
>    >
> 5. **通路分类（BRITE）**: KEGG BRITE 是对通路/基因进行层级分类的数据库，用于了解通路所属的功能大类。
>    ```bash 
>    # 从kegg数据库拉取
>    wget https://rest.kegg.jp/get/br:<org>00001 -O <org>_brite.txt
>    # 拟南芥下载示例
>    wget https://rest.kegg.jp/get/br:ath00001 -O ath_brite.txt
>
>
>    ```
>
>    > \*\*NOTE : \*\*`br:ath00001`中的`00001`为固定后缀，前面接物种代码。如番茄为`br:sly00001`，生菜为`br:lsa00001`。
>    > \*\*`ath_brite.txt`\*\***文件格式（层级结构）：**
>    >
>    > ```text title="ath_brite.txt"
>    > A09100 Metabolism
>    >   A09101 Carbohydrate metabolism
>    >     ath00010  Glycolysis / Gluconeogenesis
>    >     ath00020  Citrate cycle (TCA cycle)
>    > ...
>    > ```
>    >

***

### `2.2 KofamScan`

#### `2.2.1 KofamScan` Download

> 👩‍🌾**KOfam 数据库下载**
>
> ```markdown title="KOfam 数据库下载"
> # 2026-02-01 Version
> wget https://www.genome.jp/ftp/db/kofam/archives/2026-02-01/ko_list.gz
> wget https://www.genome.jp/ftp/db/kofam/archives/2026-02-01/profiles.tar.gz
> # 2026-01-01 Version
> wget https://www.genome.jp/ftp/db/kofam/archives/2026-01-01/ko_list.gz
> wget https://www.genome.jp/ftp/db/kofam/archives/2026-01-01/profiles.tar.gz
> ```
>
>
> > PS : 下载完成`KOfam`数据库后，就需要配置`KofamScan` 运行 `config.yaml`文件
> >
> > ```yaml title="config.yaml"
> > # Path to your KO-HMM database
> > # A database can be a .hmm file, a .hal file or a directory in which
> > # .hmm files are. Omit the extension if it is .hal or .hmm file
> > profile: <KOfam profiles path>
> >
> > # Path to the KO list file
> > ko_list: <KOfam ko_list path>
> >
> > # Path to an executable file of hmmsearch
> > # You do not have to set this if it is in your $PATH
> > # hmmsearch: /usr/local/bin/hmmsearch
> >
> > # Path to an executable file of GNU parallel
> > # You do not have to set this if it is in your $PATH
> > # parallel: /usr/local/bin/parallel
> >
> > # Number of hmmsearch processes to be run parallelly
> > cpu: 10
> > ```
> >

#### **`KofamScan`** Annotation

> 🍜\*\*使用`KofamScan`****的 ****`exec_annotation`**** 进行****`kegg`\*\***注释**
>
> ```markdown title="kofam kegg注释"
> exec_annotation \
>     input.faa \
>     -c config.yaml \
>     -o kofam_result.tsv \
>     -f detail-tsv \
>     --cpu 8 \
>     --tmp-dir ./tmp \
>     --create-alignment
> ```
>
>
> 1. **`--create-alignment`**\*\* : 在 ****`./tmp/`**** 下生成每个基因的 ****`.domain`**** 文件，包含 ****`HMM`**** 比对的详细区域信息，给 AI 做结构验证的证据\*\*
> 2. **`-f detail-tsv`**\*\* : 生成 8 列 TSV：****`gene_name`****, ****`KO`****, ****`threshold`****, ****`score`****, ****`E-value`****, ****`KO_definition`****, ****`asterisk`****（*表示通过阈值）* \*
> 3. **`-T 1`: 标准自适应阈值（bit-score based），比固定 E-value 更科学**

#### **`KofamScan`**\*\* Result\*\*​

> 🤖\*\*`KofamScan`Result\*\*​
>
> ```markdown title="KofamScan"
> # gene name           KO     thrshld  score   E-value KO definition
> #-------------------- ------ ------- ------ --------- ---------------------
>   rb_1.p1             K14183  891.50  110.9   3.4e-34 (+)-delta-cadinene synthase [EC:4.2.3.13]
> ```
>
>
> 1. **`gene name`**: ID 对应你转录组或基因组中的特定基因序列，是后续所有分析的基础;
> 2. **`KO`**:  KEGG 数据库中直系同源基因家族的唯一标识符。KO 编号是功能注释的核心，直接链接到 KEGG 通路、代谢反应和酶学信息。
> 3. **`thrshld`**\*\* ：\*\* KO 家族预设的 bit-score 通过阈值。KofamScan 为每个 KO 家族基于内部交叉验证单独校准此阈值，以最大化 F-measure。当该列显示为`-` 时，表示该 KO 在 KEGG 中代表性序列不足，尚未建立可靠的阈值。
> 4. **`score`**\*\* :\*\* 表示查询序列与 KO 家族 HMM 隐藏马尔可夫模型的比对 bit-score。得分越高，说明序列与模型匹配度越好。但需注意，必须结合`thrshld`列判断：只有当 score 大于等于 threshold 时（行首会标记`*` 星号），才视为通过阈值的高置信注释。
> 5. **`E-value`** : 表示在随机情况下获得该比对质量或更好的期望次数。数值越小统计显著性越高，通常小于 1e-5 视为显著。
> 6. **`KO definition`** : 自然语言描述的功能说明和方括号内的酶学委员会编号（EC 号）。EC 号用于精确链接到代谢反应（如`4.2.3.13` 表示裂解酶类，作用于碳-氧键），是理解基因生物学功能的关键。

### 2.3 eggnog-mapper

#### 2.3.1 download eggnog-mapper dataset

> 🏃‍♀️\*\*使用自动脚本下载最新的`eggnog-mapper`\*\***数据库**
>
> ```bash title="download eggnog-mapper v5"
> download_eggnog_data.py -y -F -M -P --data_dir /home/zj/database/eggnog6/ 
> ```
>

> 🌴**手动下载`eggnog5`&****`eggnog6`**** ****`novel`**** 数据库**
>
> ```bash title="downlaod eggnog5 & eggnog6  novel"
> # 下载并解压核心库 (eggnog.db)
> wget http://eggnog5.embl.de/download/emapperdb-5.0.2/eggnog.db.gz
> # 下载并解压物种分类树库
> wget http://eggnog5.embl.de/download/emapperdb-5.0.2/eggnog.taxa.tar.gz
> # 下载并解压全物种 Diamond 索引
> wget http://eggnog5.embl.de/download/emapperdb-5.0.2/eggnog_proteins.dmnd.gz
> # 下载并解压新基因家族库 (对应 -F)
> wget http://eggnog6.embl.de/download/novel_fams-1.0.1/novel_fams.dmnd.gz
> wget http://eggnog6.embl.de/download/novel_fams-1.0.1/novel_fams.pkl.gz
> # 下载并解压 MMseqs2 和 Pfam 库 (对应 -M 和 -P)
> wget http://eggnog5.embl.de/download/emapperdb-5.0.2/mmseqs.tar.gz
> wget http://eggnog5.embl.de/download/emapperdb-5.0.2/pfam.tar.gz
>
> ```
>
>
> 下载完成所有的`eggnog`数据后，就可以按照下面目录的结构，对相关文件进行处理。
>
> ```bash title="本地eggnog_db目录"
> eggnog_db/
> ├── eggnog.db              # 解压后的 SQLite 数据库（3.5G）
> ├── eggnog.taxa/           # 解压后的分类树目录
> ├── eggnog_proteins.dmnd.gz    # ❗保持压缩（15G）
> ├── novel_fams.dmnd.gz         # ❗保持压缩（2G）
> ├── novel_fams.pkl.gz          # ❗保持压缩（500M）
> ├── mmseqs/                # 解压后的 MMseqs2 索引（可选）
> └── pfam/                  # 解压后的 Pfam 目录（可选）
> ```
>

#### 2.3.2 KEGG Annotation by `emapper.py`

> 😇\*\*`Standard Annotation`\*\*
>
> ```bash title="常规注释参数"
> # 使用 emapper.py 进行 kegg 注释
> emapper.py -i input.faa \
>            --data_dir ./eggnog5_db/ \
>            -o result --cpu 8
> ```
>
>
> 1. `-i` : 输入蛋白序列文件（`FASTA` 格式）;
> 2. `--data_dir`:指向你下载的数据库目录;
> 3. `-o` : 输出文件前缀;
> 4. `--cpu`并行线程数（建议设为服务器核心数）。

> 🪛**质量控制参数**
>
> ```bash title="质量控制参数"
> emapper.py -i input.faa \
>            --data_dir ./eggnog5_db/ \
>            -o result \
>            --cpu 16 --tax_scope bacteria \
>            --seed_ortholog_evalue 1e-5 \
>            --report_orthologs
> ```
>
>
> 1. `--tax_scope` : 限制物种范围，避免跨界注释错误 `bacteria` 或 `eukaryota`;
> 2. `--seed_ortholog_evalue` : 控制种子 ortholog 的严格程度，直接影响后续 KO 注释可靠性
>    - 模式生物（人/小鼠/酵母/大肠杆菌等）,可以使用用 `1e-10`（高置信）
>    - 非模式生物（新测序菌株、环境样本）,用 `1e-5`（防漏检）
>    - 宏基因组（MAGs）,用 `1e-5`（序列碎片化，需要更宽松阈值补偿）
> 3. `--evalue` : 比对过滤阈值，太宽松会引入噪声 (可以使用`1e-3`);
> 4. `--report_orthologs`:输出所有直系同源基因，而不仅是最佳匹配。

> 🐢\*\*`dna`\*\***序列注释**
>
> ```bash title="dna序列注释"
> emapper.py -i genome.fa \
>            --itype genome -\
>            -genepred prodigal \
>            --data_dir ./eggnog5_db/ \
>            -o genome_result --cpu 16
> ```
>
>
> 1. `--itype`:如果输入是基因组`DNA` 或宏基因组 `contigs`，自动预测基因并翻译 (`genome` 或 `metagenome`);
> 2. `--genepred`:基因预测方法：`search` 用 `blastx `快但粗糙，`prodigal` 精准但慢；
> 3. `--translate` : 如果是 `CDS` 序列（核酸），强制翻译为蛋白。

> 😔\*\*`Standard Annotation`- \*\*​**`Novel Families`**
>
> `eggnog6`版本数据库增加了新的基因家族的注释，`novel_fams`为更新的数据库，在完整标注释后，就可以继续\*\*`Novel Families`\*\*注释了。
>
> ```bash title="Standard Annotation + Novel Families"
> # 标准注释 (Standard Annotation)
> emapper.py -i input.faa -m diamond \
>            --data_dir ./eggnog5_db/ \
>            -o result_main
> # 新家族发现 (Novel Families)
> emapper.py -i input.faa -m novel_fams \
>            --data_dir ./eggnog5_db/ \
>            -o result_novel
>
> ```
>

#### 2.3.3 Result

> 🍜\*\*`emapper.py`\*\***注释完成后，主要会在文件夹下生成以下三个注释文件:**
>
> 1. `emapper.annotations` : **eggNOG-mapper 的标准注释结果文件**,格式为制表符分隔的 TSV;
>    - **query** : 查询序列 ID（你的基因）
>    - **subject** :参考序列 ID（格式：`taxid.protein_id`）
>    - **pident** :百分比序列同一性（% identity）
>    - **length**：比对区域长度（氨基酸残基数）
>    - **mismatch** : 比对区内的错配数
>    - **gapopen** ：缺口（gap） opening 数
>    - **qstart** ：查询序列比对起始位置
>    - **qend** ：查询序列比对结束位置
>    - **sstart** ：参考序列比对起始位置
>    - **send** ：参考序列比对结束位置
>    - **evalue** ：期望阈值（越小说明显著性越高）
>    - **bitscore** ： 比对得分（越高越好）
>    - **qcov** ：**Query Coverage**：查询序列被比对的覆盖率（%）
>    - **scov** ：**Subject Coverage**：参考序列被比对的覆盖率（%）
> 2. **`emapper.hits`** 文件，包含**所有显著的比对 hits**（而不仅仅是 `annotations` 文件中的最佳 hit）。这是原始 DIAMOND 比对输出，用于深度分析旁系同源和比对质量；
> 3. **`result.emapper.seed_orthologs`** 文件，是 `eggNOG-mapper` 的**中间结果文件**。

***

## 3 Reference

[^1]: [https://www.kegg.jp/kegg/rest/keggapi.html](https://www.kegg.jp/kegg/rest/keggapi.html "https://www.kegg.jp/kegg/rest/keggapi.html")

[^2]: [https://github.com/takaram/kofam\_scan](https://github.com/takaram/kofam_scan "https://github.com/takaram/kofam_scan")

[^3]: [https://github.com/eggnogdb/eggnog-mapper](https://github.com/eggnogdb/eggnog-mapper "https://github.com/eggnogdb/eggnog-mapper")
