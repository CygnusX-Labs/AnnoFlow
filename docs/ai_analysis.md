# AnnoFlow AI 注释分析

AnnoFlow 支持 AI 驱动的**逐蛋白可靠性评估**（模块开关 `ai: true`，默认关闭），而非仅样本级汇总统计。AI 参数集中在 analysisyaml 的 `ai_config` 段。

- 模块开关与依赖自动启用见 [usage.md](usage.md)

---

## 功能特点

- **逐蛋白可靠性评估**: 对每条蛋白分别评估 eggNOG 和 KofamScan 的可靠性
- **物种合理性判断**: 结合 `taxonomy` 参数，判断注释功能对该物种是否合理
- **Tax_scope 精确度检查**: 评估 eggNOG `tax_scope` 与物种分类的匹配层级
- **KofamScan 阈值比值解读**: 结合 KO 类型（管家基因 vs 稀有基因）判断 ratio 可信度
- **工具一致性检测**: 自动标记 eggNOG 与 KofamScan 的 KO 冲突
- **分层筛选降本**: 高置信/低质量两端由规则直接判定，仅模糊区域送 AI
- **Token 消耗追踪**: 自动统计 prompt/completion/total tokens，便于成本控制

## 支持的 AI 提供商

| 提供商 | 模型示例 | 特点 |
|--------|---------|------|
| **Ollama** (默认) | llama3.2, mistral | 本地运行，无需联网，免费 |
| **OpenAI** | gpt-4, gpt-3.5-turbo | 云端 API，性能强 |
| **Claude** | claude-3-sonnet | 云端 API，擅长长文本 |

## 快速开始

### 1. 使用本地 Ollama（推荐）

```bash
# 安装 Ollama
curl -fsSL https://ollama.com/install.sh | sh

# 下载模型（以 llama3.2 为例，4GB 左右）
ollama pull llama3.2

# 确认服务运行
curl http://localhost:11434/api/tags
```

### 2. 在 analysisyaml 中启用 AI

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

### 3. 运行分析

```bash
# 运行完整流程（包含 AI 分析）
snakemake -s /path/to/AnnoFlow/snakefile --cores 8 --use-conda --conda-frontend mamba \
  --config analysisyaml=/path/to/project.yaml

# 或仅运行 AI 分析（已有注释结果时）
snakemake -s /path/to/AnnoFlow/snakefile --cores 8 --use-conda --conda-frontend mamba \
  --config analysisyaml=/path/to/project.yaml ai_analysis
```

## 输出结果

```
04.ai/
├── {sample}_ai_report.md          # AI 逐蛋白评估报告（Markdown）⭐
├── {sample}_ai_analysis.json      # 结构化评估数据（JSON）⭐
├── {sample}_ai_analysis.tsv       # 评估结果 TSV
├── {sample}_ai_analysis.csv       # 评估结果 CSV
└── AI_MULTI_SAMPLE_SUMMARY.md     # 多样本汇总（多样本时）
```

### AI 报告内容示例

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

## 分层筛选策略说明

为控制 Token 成本，`ai_curator.py` 默认开启**分层筛选**（可将 `ai_config.no_auto_filter` 设为 `true` 关闭）：

| 分类 | 判定标准 | 处理方式 | Token 消耗 |
|------|----------|----------|-----------|
| **高置信** | `e-value < 1e-10` **且** `Kofam ratio > 1.5` | 规则直接 `Accept` | 0 |
| **低质量** | `e-value > 1e-3` **或** `Kofam ratio < 0.5` | 规则直接 `Reject` | 0 |
| **模糊区域** | 其余蛋白 | 送 AI 评估 | 有 |

这意味着对于一个 3000 蛋白的基因组，可能只有 300-600 个蛋白进入模糊区域，再按 `max_proteins` 限制后，实际 API 调用可能只有几十个，大幅降低成本。

---

## API 密钥安全指南 🔒

**⚠️  绝对不要直接在配置文件中写入真实 API key！**

### 安全风险对比

| 方式 | 风险等级 | 说明 |
|------|---------|------|
| 明文写在 yaml 配置 | 🔴 极高 | 可能被提交到 Git，泄露密钥 |
| 命令行参数传递 | 🟠 高 | 会被记录在 shell 历史和进程列表 |
| 环境变量（✅ 推荐） | 🟢 低 | 只在内存中存在，不会持久化到文件 |

### 推荐做法：使用环境变量

**步骤 1：设置环境变量（在运行前）**

```bash
# 方式 1：当前 shell 会话（推荐用于测试）
export AI_API_KEY="sk-your-actual-api-key"

# 方式 2：写入 ~/.bashrc 或 ~/.zshrc（长期有效）
echo 'export AI_API_KEY="sk-your-actual-api-key"' >> ~/.bashrc
source ~/.bashrc
```

**步骤 2：在 ai_config 中只写变量名**

```yaml
ai: true
ai_config:
  provider: "openai"
  model: "glm-4.7"
  api_key: "AI_API_KEY"      # ← ✅ 只写变量名，不写真实 key
  api_base: "https://dashscope.aliyuncs.com/compatible-mode/v1"
```

**步骤 3：运行分析**

```bash
snakemake -s /path/to/AnnoFlow/snakefile --cores 8 --use-conda --conda-frontend mamba \
  --config analysisyaml=/path/to/project.yaml
```

### 安全机制说明

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