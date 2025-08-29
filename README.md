# Anki 写卡助手

基于大语言模型的 Anki 卡片生成与导出工具，提供命令行与 Web 双形态使用方式，支持自定义模板、丰富提示词体系与统一导出。

## 主要特性

- 强大的卡片生成能力：内置填空与选择题等多种提示词，支持难度控制与批量生成
- 统一导出：一次生成，支持 JSON、CSV、APKG、TXT、HTML 多种格式
- 模板系统：支持 `Quizify` 与 `Quizify Enhanced Cloze`，可扩展自定义模板
- Web 界面：提供可视化生成、预览、历史记录与下载
- 文件处理：支持从文本、Markdown、Word、PDF、Excel 等文件提取内容
- 灵活配置：可视化管理 LLM、导出、生成等参数，设置实时生效

## 架构概览

```
src/
├─ core/
│  ├─ card_generator.py        # 卡片生成：提示词组装、结构化输出、模型字段映射
│  ├─ llm_client.py            # 大语言模型管理：统一的 LLM 客户端与配置
│  └─ unified_exporter.py      # 统一导出器：JSON/CSV/TXT/HTML/APKG
├─ prompts/                    # 提示词体系：按模板和类型组织，可用户自定义覆盖
├─ templates/                  # 模板管理：加载卡片模板与资源
├─ utils/                      # 通用工具：配置与文件处理
└─ web/                        # Web 服务：Flask + Socket.IO API 与页面

Card Template/                 # 外部模板资源目录（HTML/CSS 等）
output/                        # 导出输出目录
logs/                          # 运行日志
main.py                        # 入口：CLI 与 Web 启动器
```

核心流程：
- 文本或文件内容 → 选择模板与提示词 → LLM 结构化返回 → 统一映射为 `CardData` → 导出器多格式落盘。

## 安装与运行

### 环境依赖

```bash
pip install -r requirements.txt
# 开发可选
pip install -r requirements-dev.txt
```

### 初始化配置

```bash
cp config.json.example config.json
```

编辑 `config.json`（关键项如下）：

```json
{
  "llm": {
    "api_key": "your-api-key",
    "base_url": "https://api.openai.com/v1",
    "model": "gpt-3.5-turbo",
    "temperature": 0.7,
    "max_tokens": 20000,
    "timeout": 30
  },
  "generation": {
    "default_difficulty": "medium",
    "default_card_count": 1
  },
  "export": {
    "default_formats": ["json", "apkg"],
    "output_directory": "output"
  },
  "templates": {
    "directory": "Card Template"
  }
}
```

### 命令行使用

```bash
# 从纯文本生成
python main.py --content "你的学习内容" --template "Quizify" --prompt cloze --count 3

# 从文件生成（txt/md/docx/pdf/xlsx 等，按实际支持为准）
python main.py --file "path/to/file.docx" --template "Quizify Enhanced Cloze"

# 指定导出格式
python main.py -c "内容" -e json csv html txt apkg

# 列出可用模板/提示词/已配置的 LLM 客户端
python main.py --list-templates
python main.py --list-prompts
python main.py --list-llms
```

常用参数：
- `--template/-t`: 模板名称，默认 `Quizify`
- `--prompt/-p`: 提示词类型，默认 `cloze`（增强填空模板会自动映射为 `enhanced_cloze`）
- `--count`: 生成卡片数量，默认读取配置 `generation.default_card_count`
- `--export/-e`: 导出格式列表，默认读取配置并强制包含 `json`
- `--difficulty`: `easy|medium|hard`

### Web 界面

```bash
python main.py --web --host 0.0.0.0 --port 5000 --debug
```

打开浏览器访问 `http://localhost:5000`，可完成：
- 在线生成与实时进度反馈
- 查看与下载导出文件（历史记录）
- 在线查看与编辑提示词，支持重置为原始版本
- 可视化配置 LLM（API Key、base_url、模型、温度等）

## 提示词与模板

### 提示词组织
- 全局目录：`src/prompts`
- 模板子目录优先：如 `src/prompts/quizify`、`src/prompts/enhanced_cloze`
- 用户覆盖：同名文件加后缀 `_user.md`，例如 `cloze_user.md`。若存在将优先加载

在 Web 界面中可以直接读取/保存/重置提示词；CLI 下由 `BasePromptManager` 自动解析。

### 模板体系
- 外部模板资源位于 `Card Template/`，对应 `Quizify` 与 `Quizify Enhanced Cloze` 等
- 模板加载与字段映射由 `src/templates/template_manager.py` 管理
- APKG 导出时会优先使用已注册模板生成 `Model/Note`；找不到模板则回退到内置基础/填空模型

## 文件与格式支持

输入：
- 纯文本、Markdown
- Word（.docx）、PDF（.pdf）、Excel（.xlsx）等常见文档（按 `FileProcessor` 实际支持为准）

输出：
- JSON（含元数据，记录生成时的配置与内容摘要）
- CSV（含字段表头）
- TXT（人类可读的预览文本）
- HTML（简洁预览页）
- APKG（可直接导入 Anki）

历史记录与下载：
- Web 界面提供 `/api/history` 查询与 `/download/<filename>` 下载能力
- 导出文件统一保存在 `output/` 目录

## 常见用法示例

```bash
# 生成 5 张中等难度的 Quizify 卡片，并导出 JSON+APKG
python main.py -c "操作系统进程与线程的区别" -t Quizify -p cloze --count 5 -e json apkg

# 从 Markdown 文档的各段落批量生成卡片
python main.py -f notes.md -t "Quizify Enhanced Cloze" -p cloze -e json html
```

## 故障排除

1) LLM 请求被拦截或返回 HTML 页面
- 若使用第三方反代域名，可能存在 Cloudflare 人机验证或网关返回 HTML。请将 `llm.base_url` 改为可直连的后端 API 域名（如官方 `https://api.openai.com/v1` 或服务商提供的后端域名）。

2) 无法下载历史导出文件（Windows 路径）
- Web 下载接口已做路径归一化处理，如仍失败，请检查 `output/` 目录以及文件是否存在。

3) 模板未找到或渲染异常
- 确认模板目录与名称与 `config.json` 中 `templates.directory` 保持一致
- 确认模板在 `template_manager` 中已正确注册

4) 导出失败
- 检查磁盘空间与目录权限
- 确认导出格式书写正确；`json` 会被强制加入导出列表

日志位置：`logs/app.log`。

## 二次开发

- 新增模板：
  1. 在 `Card Template/` 下创建模板文件夹，提供 HTML/CSS 等资源
  2. 在 `src/templates/template_manager.py` 注册模板及字段
  3. 使用 `UnifiedExporter` 的模板导出能力测试 APKG

- 扩展提示词：
  1. 在 `src/prompts/` 或其子目录增加对应的 `.md`
  2. 用户改写可通过新增同名 `_user.md` 文件完成覆盖

- 新增导出格式：
  - 在 `src/core/unified_exporter.py` 添加导出方法，并在 `export_multiple_formats` 注册

## 许可证

本项目采用 MIT 许可证。详见 `LICENSE` 文件。

## 版本记录

v1.0.0（2025-08-29）
- 初始版本，提供 CLI 与 Web 使用方式
- 支持多模板与多格式导出
- 提供历史记录与下载
