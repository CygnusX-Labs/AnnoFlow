# AnnoFlow 常见问题

### Q1: 首次运行很慢？

A: 首次运行时需要下载并创建 Conda 环境，可能需要 10-30 分钟。环境创建后会缓存，后续运行会很快。

### Q2: eggnog-mapper 找不到数据库？

A: 确认 analysisyaml 中的 `reference_path` 指向参考目录根，且其下存在 `dataset/eggnog-mapper/`（含 `eggnog.db`）与 `dataset/kegg_<date>_ko_dataset/`。参考路径在启动时 fail-fast 检查，先跑 dry-run（`-n`）即可暴露路径错误。数据库准备见 [database_preparation.md](database_preparation.md)。

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

A: 这是正常的成本控制设计。默认开启分层筛选：高置信和低质量蛋白由规则直接判定，只有模糊区域才送 AI。如需扩大评估量，在 analysisyaml 的 `ai_config` 中调大 `max_proteins`；全量评估则设 `no_auto_filter: true`（⚠️ 会消耗大量 Token）。详见 [ai_analysis.md](ai_analysis.md)。

### Q7: 输入文件名带复合扩展名（如 `.fa.TD2.1k.pep`）如何配置？

A: 输入解析已支持复合扩展名。样本表 `sample` 列写基础名即可：

```csv
sample,sample_name
rnabloom_transcript_LongOrfs,RNA-Bloom ORFs
```

系统会自动匹配 `rnabloom_transcript_LongOrfs.fa.TD2.1k.pep`。

### Q8: 为什么 `--config ai=false` 关不掉 AI 模块？

A: 命令行 `--config` 的布尔值会被解析为字符串，非空字符串恒为真。关闭模块请在 analysisyaml 中写 `ai: false`（其余模块开关同理）。