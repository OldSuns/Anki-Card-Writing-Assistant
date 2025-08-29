# Anki写卡助手

基于大语言模型的Anki记忆卡片生成工具，支持多种格式导出和自定义模板。

## 功能特性

- 🤖 **AI驱动**: 基于大语言模型自动生成高质量的Anki卡片
- 📝 **多种格式**: 支持JSON、CSV、APKG、TXT、HTML等多种导出格式
- 🎨 **自定义模板**: 支持Quizify和增强填空等多种卡片模板
- 📁 **文件处理**: 支持Word、PDF、Excel等多种文件格式
- 🌐 **Web界面**: 提供友好的Web操作界面
- ⚙️ **灵活配置**: 支持自定义LLM配置和生成参数

## 快速开始

### 安装依赖

```bash
# 安装运行时依赖
pip install -r requirements.txt

# 开发环境（可选）
pip install -r requirements-dev.txt
```

### 配置API密钥

复制配置文件模板并设置你的API密钥：

```bash
cp config.json.example config.json
```

编辑 `config.json` 文件，设置你的LLM API配置：

```json
{
  "llm": {
    "api_key": "your-api-key-here",
    "base_url": "https://api.openai.com/v1",
    "model": "gpt-3.5-turbo"
  }
}
```

### 基本使用

#### 命令行模式

```bash
# 生成卡片
python main.py --content "你的学习内容" --template Quizify

# 从文件生成
python main.py --file "your-file.docx" --template "Quizify Enhanced Cloze"

# 查看可用模板
python main.py --list-templates

# 查看可用提示词
python main.py --list-prompts
```

#### Web界面

```bash
# 启动Web服务器
python main.py --web --debug
```

然后在浏览器中访问 `http://localhost:5000`

## 项目结构

```
Anki Card Writing Assistant/
├── src/
│   ├── core/                 # 核心功能模块
│   │   ├── card_generator.py    # 卡片生成器
│   │   ├── llm_client.py        # LLM客户端
│   │   └── unified_exporter.py  # 统一导出器
│   ├── prompts/              # 提示词模板
│   ├── templates/            # 模板管理器
│   ├── utils/                # 工具模块
│   └── web/                  # Web界面
├── Card Template/            # 卡片模板
│   ├── Quizify/              # Quizify模板
│   └── Quizify Enhanced Cloze/       # 增强填空模板
├── output/                   # 导出文件目录
├── logs/                     # 日志文件
├── main.py                   # 主程序入口
├── config.json              # 配置文件
└── requirements.txt          # 依赖列表
```

## 支持的格式

### 输入格式
- **文本**: 直接输入文本内容
- **Word文档**: `.docx` 格式
- **PDF文件**: `.pdf` 格式
- **Excel文件**: `.xlsx` 格式
- **文本文件**: `.txt` 格式

### 输出格式
- **JSON**: Anki导入格式，包含元数据
- **CSV**: 表格格式，适合批量处理
- **APKG**: Anki包格式，可直接导入Anki
- **TXT**: 纯文本格式，便于阅读
- **HTML**: 网页格式，支持预览

## 模板系统

### Quizify模板
- 现代化的卡片设计
- 支持多种交互功能
- 适合问答类卡片

### 增强填空模板
- 支持编号填空语法
- 兼容注释和更多内容区块
- 适合填空题卡片

## 配置说明

### LLM配置
```json
{
  "llm": {
    "api_key": "API密钥",
    "base_url": "API基础URL",
    "model": "模型名称",
    "temperature": 0.7,
    "max_tokens": 20000,
    "timeout": 30
  }
}
```

### 生成配置
```json
{
  "generation": {
    "default_difficulty": "medium",
    "default_card_count": 1
  }
}
```

### 导出配置
```json
{
  "export": {
    "default_formats": ["json", "apkg"],
    "output_directory": "output"
  }
}
```

## 开发指南

### 添加新模板

1. 在 `Card Template/` 目录下创建新模板文件夹
2. 添加模板文件（HTML、CSS等）
3. 在 `src/templates/template_manager.py` 中注册模板

### 添加新提示词

1. 在 `src/prompts/` 目录下创建新的提示词文件
2. 使用Markdown格式编写提示词
3. 系统会自动加载新的提示词

### 扩展导出格式

1. 在 `src/core/unified_exporter.py` 中添加新的导出方法
2. 在 `export_multiple_formats` 方法中注册新格式

## 故障排除

### 常见问题

1. **API连接失败**
   - 检查API密钥是否正确
   - 确认网络连接正常
   - 验证API基础URL是否正确

2. **模板加载失败**
   - 检查模板目录结构是否正确
   - 确认模板文件是否存在
   - 查看日志文件获取详细错误信息

3. **导出失败**
   - 检查输出目录权限
   - 确认磁盘空间充足
   - 验证文件格式是否正确

### 日志查看

日志文件位于 `logs/app.log`，包含详细的运行信息和错误日志。

## 贡献指南

1. Fork 项目
2. 创建功能分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 打开 Pull Request

## 许可证

本项目采用 MIT 许可证 - 查看 [LICENSE](LICENSE) 文件了解详情。

## 更新日志

### v1.0.0 (2025-08-29)
- 🎉 初始版本发布
- ✨ 支持多种输入输出格式
- 🎨 提供多种卡片模板
- 🌐 集成Web界面
- 🔧 统一的导出器架构
- 📁 优化的目录结构
