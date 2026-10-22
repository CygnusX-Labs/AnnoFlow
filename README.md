<p align="center">
  <img src="docs/AnnoFlow_logo.png" alt="AnnoFlow logo" width="160">
</p>

# AnnoFlow

**Language / 语言**: English | [简体中文](docs/README.zh-CN.md)

Gene functional annotation pipeline (a member of the Flow family): eggnog-mapper provides full-spectrum functional annotation across KEGG/GO/COG/EC/Pfam/CAZy, KofamScan provides KO cross-validation, and the integration layer arbitrates conflicts between the two tools, with optional AI-driven per-protein reliability review. Built on Snakemake + Conda, featuring modular design, quality filtering, confidence assessment, and integrated delivery & reporting.

Version: `AnnoFlow v1.0.0` (the single source of truth for the version is `pipeline_version` in `config/config.yaml`).

> **License**: AnnoFlow is released under the [MIT License](./LICENSE).

## 🤝 Working with RNAFlow

AnnoFlow is designed to work alongside [RNAFlow](https://github.com/xsx123123/RNAFlow). Non-model organisms usually lack ready-made gene functional annotations; AnnoFlow generates standardized KO / GO annotations for their protein sequences via eggnog-mapper and KofamScan, and the `export_rnaflow_annotation` rule exports an annotation table that RNAFlow can consume directly (`rnaflow_annotation.tsv` + `kegg_pathway_names.tsv`), feeding downstream enrichment analysis. See the [Pipeline & Results Guide](docs/pipeline.md) for the export format and integration details.

<p align="center">
  <img src="docs/AnnoFlow与RNAFlow共享注释参考库流程.png" alt="Diagram of the shared annotation reference library flow between AnnoFlow and RNAFlow" width="720">
</p>

## Features

- ✅ **Modular design**: Rules are numbered by step (01-09); each module can be toggled independently, and disabled modules drop out of the DAG automatically
- ✅ **Hard MD5 gating on inputs**: Annotation starts only after all sample inputs pass verification, preventing a full run on wrong or corrupted data
- ✅ **Quality filtering**: Multi-dimensional filtering based on E-value, bit-score, and more
- ✅ **Confidence assessment**: Three-tier confidence grading (High/Medium/Low) with a 0-100 scoring system
- ✅ **Result integration**: Horizontal integration of eggnog and KofamScan results with KO conflict arbitration
- ✅ **Multi-sample merging**: Merges results across samples with KEGG consistency comparison for downstream analysis
- ✅ **Conda environments**: Automatic dependency management (mamba-accelerated) for reproducibility
- ✅ **AI-driven analysis (optional)**: Per-protein reliability assessment (Ollama/OpenAI/Claude) with tiered filtering and token usage tracking
- ✅ **Delivery & reporting**: Automatically generates a delivery manifest (manifest + MD5) and `project_summary.json`
- ✅ **Flexible input**: Supports `.pep`, `.fa`, `.fasta`, `.faa`, `.protein`, and compound extensions (e.g. `.fa.TD2.1k.pep`)
- ✅ **Schema-enforced validation**: Project config is validated at startup; path errors fail fast without wasting cluster resources

## Flow Family Architecture

AnnoFlow conforms to the Flow framework spec (`Standard/FlowFrame` submodule). Config precedence chain:

```
config defaults (repo) < analysisyaml (project-level) < --config key=value (command line)
```

Module toggles (`config/config.yaml`; put module toggles in your analysisyaml — do not pass booleans via `--config`):

| Module | Default | Description |
|------|------|------|
| eggnog | true | eggnog-mapper functional annotation (KEGG/GO/COG/EC/Pfam/CAZy) |
| kofamscan | true | KofamScan KO annotation |
| integrate | true | Two-tool integration scoring and conflict arbitration |
| merge | true | Multi-sample merging, KO consistency comparison, and summary |
| ai | false | AI per-protein reliability assessment (requires `ai_config`) |
| deliver | true | Deliver delivery_manifest (copy mode) |
| report | true | `project_summary.json` minimal report |

Automatic dependency enabling: when a downstream module is enabled, missing upstream modules are turned on automatically with a warning logged. See the [User Guide](docs/usage.md) for details on the config files, the sample sheet, delivery/reporting, and monitoring push.

## Directory Structure

```
.
├── snakefile                      # Main workflow: config loading, schema validation, target generation
├── monitor_config.yaml            # OmicHub monitoring push config template (optional)
├── config/                        # Default config files + sample sheet template
│   ├── config.yaml                # Pipeline control: version, module toggles, ai_config, script path table
│   ├── reference.yaml             # Database reference paths (resolved relative to reference_path)
│   ├── run_parameter.yaml         # Threads and filtering thresholds
│   ├── cluster_config.yaml        # HPC resource profiles and queue mapping
│   └── samples.csv                # Sample sheet template (sample,sample_name)
├── schema/
│   └── config.schema.yaml         # Config schema enforced at startup
├── examples/
│   └── analysisyaml.example.yaml  # Project-level config example (copy and edit before use)
├── rules/                         # Snakemake rules (numbered by step 01-09)
│   ├── 01.common.smk              # Common helper functions (input file parsing; no business rules)
│   ├── 02.input_md5.smk           # Input MD5 verification gate
│   ├── 03.eggnog.smk              # eggnog-mapper annotation and result processing
│   ├── 04.kofamscan.smk           # KofamScan annotation and result processing
│   ├── 05.integrate.smk           # eggnog + KofamScan integration scoring
│   ├── 06.merge.smk               # Multi-sample merge / KO consistency comparison / summary
│   ├── 07.ai_curator.smk          # AI per-protein reliability assessment (optional)
│   ├── 08.deliver.smk             # Delivery manifest
│   ├── 09.Report.smk              # project_summary.json
│   └── utils/                     # Framework utilities (target generation, config validation, resources, logging, etc.)
├── scripts/                       # Python processing scripts (eggnog/kofamscan_processor,
│                                  #   integrate/merge, export_rnaflow_annotation,
│                                  #   ai_curator, check_input_md5, deliver, etc.)
├── env/                           # Conda environment files (eggnog-mapper / kofamscan / py3.12 / openai)
├── docs/                          # Documentation (see the index below)
├── Standard/FlowFrame             # Flow framework spec (submodule)
└── test/
    └── TD2.1k.pep                 # Test data (1000 protein sequences)
```

## Quick Start

### 1. Prerequisites

Make sure [Snakemake](https://snakemake.readthedocs.io/) (9.9.0+) and [Conda](https://docs.conda.io/) are installed (Miniconda + mamba recommended):

```bash
conda install -n base -c conda-forge -c bioconda snakemake
```

### 2. Prepare the database directory

```
<reference_path>/
└── dataset/
    ├── eggnog-mapper/                  # eggnog-mapper databases (eggnog.db, etc.)
    ├── kegg_<date>_ko_dataset/         # KofamScan ko_list + profiles
    └── kegg_pathway_names.tsv          # KEGG pathway name cache (auto-generated on first run, reused offline)
```

See the [Reference Database Preparation Guide](docs/database_preparation.md) for how to download, generate, and deploy the three database components.

### 3. Write the project-level config (analysisyaml)

```bash
cp examples/analysisyaml.example.yaml /path/to/project.yaml
vim /path/to/project.yaml
```

Fill in the seven schema-required fields (the five path keys must be absolute paths):

```yaml
project_name: my_annotation_project
species: Dioscorea_alata
sample_csv: /data/project/01.workflow/samples.csv   # follow the config/samples.csv template
workflow: /data/project/01.workflow                 # working directory (Snakemake workdir)
data_deliver: /data/project/02.data_deliver
input_dir: /data/project/00.protein                 # input protein sequence directory
reference_path: /data/jzhang/reference/AnnoFlow
```

### 4. Run

```bash
# dry-run: inspect the execution plan and surface config/path errors
snakemake -s /path/to/AnnoFlow/snakefile -n \
  --config analysisyaml=/path/to/project.yaml

# full run
snakemake -s /path/to/AnnoFlow/snakefile --cores 8 --use-conda --conda-frontend mamba \
  --rerun-triggers mtime --logger rich-loguru \
  --config analysisyaml=/path/to/project.yaml
```

Common targets: `annotate` (annotation only), `reports` (analysis summary), `merge` (multi-sample merging), `ai_analysis` (AI analysis). See the [User Guide](docs/usage.md) for the full set of commands and parameters.

## Pipeline Overview

```
Input protein sequences → 01.qc hard MD5 gate
                        → 01.eggnog / 02.kofam dual-tool annotation and quality filtering
                        → 03.merge integration scoring + multi-sample merging + KO consistency + RNAFlow export
                        → 04.ai per-protein AI reliability assessment (optional)
                        → data_deliver delivery manifest + project_summary.json
```

| Output | Contents |
|------|------|
| `01.qc/md5_check.tsv` | Input MD5 verification results (gate file) |
| `01.eggnog/` | eggnog-mapper annotation results and confidence assessment ⭐ |
| `02.kofam/` | KofamScan annotation results and confidence assessment |
| `03.merge/` | Integration scoring, multi-sample merging, KO consistency, GO/KO export, `rnaflow_annotation.tsv` ⭐ |
| `04.ai/` | AI per-protein assessment reports (optional) |
| `{data_deliver}/` + `project_summary.json` | Delivery manifest and project summary |

See the [Pipeline & Results Guide](docs/pipeline.md) for the full pipeline diagram, per-step rule descriptions, output file formats, and how to read the statistics reports.

## Documentation

The detailed guides under `docs/` are currently written in Chinese; the Chinese README is available [here](docs/README.zh-CN.md).

| Document | Contents |
|------|------|
| [User Guide](docs/usage.md) | Config system, module toggles, common commands, test data, standalone script usage, migration from older versions |
| [Reference Database Preparation Guide](docs/database_preparation.md) | Download, generation, and deployment of eggnog / KOfam / KEGG pathway name mappings |
| [Pipeline & Results Guide](docs/pipeline.md) | Pipeline diagram, per-step notes, output file structure and formats, RNAFlow integration |
| [AI Annotation Analysis](docs/ai_analysis.md) | Per-protein assessment, tiered filtering strategy, API key safety |
| [FAQ](docs/faq.md) | Common issues with running, databases, filtering, multi-sample handling, AI, etc. |
| [Filtering & Confidence Standards](docs/filtering_standards.md) | Detailed explanation of the two processors' scoring systems and threshold references |
| [KEGG Annotation Tools Tutorial](docs/kegg-annotation.md) | Principles and manual usage of KEGG REST / KofamScan / eggnog-mapper |

External references: [Snakemake](https://snakemake.readthedocs.io/) · [eggnog-mapper](https://github.com/eggnogdb/eggnog-mapper) · [KofamScan](https://www.genome.jp/tools/kofamkoala/)

## Dependencies

- Python 3.12 (`env/py3.12.yaml`: pandas, loguru, rich, requests, etc.)
- eggnog-mapper 2.1.13 (`env/eggnog-mapper.yaml`)
- KofamScan 1.3.0 (`env/kofamscan.yaml`)
- Snakemake 9.9.0+
- Conda/Mamba

## Citation

If you use this pipeline, please cite:

1. eggNOG-mapper v2: [https://doi.org/10.1093/molbev/msab293](https://doi.org/10.1093/molbev/msab293)
2. eggNOG 5.0: [https://doi.org/10.1093/nar/gky1085](https://doi.org/10.1093/nar/gky1085)
3. KofamScan: [https://doi.org/10.1093/bioinformatics/btz859](https://doi.org/10.1093/bioinformatics/btz859)
