# Anki写卡助手

基于大语言模型的Anki记忆卡片生成工具，支持多种LLM API和模板格式。

## 功能特性

### 🎯 核心功能
- **智能卡片生成**: 基于大语言模型自动生成高质量的Anki记忆卡片
- **多模板支持**: 支持Quizify和增强填空等多种Anki模板
- **多LLM支持**: 支持OpenAI、Claude、本地LLM等多种大语言模型
- **批量处理**: 支持从文件批量生成卡片
- **多格式导出**: 支持JSON、CSV、HTML、TXT、APKG等多种导出格式
- **APKG导出**: 使用genanki模块直接生成Anki可导入的.apkg文件

### 🎨 模板系统
- **Quizify模板**: 支持问答、选择、填空等多种交互功能
- **增强填空模板**: 支持提示、动画等高级填空功能
- **自定义模板**: 支持创建和导入自定义模板

### 🤖 LLM集成
- **统一接口**: 使用OpenAI兼容接口，支持所有兼容的LLM服务
- **灵活配置**: 支持OpenAI、Claude、本地LLM等任何OpenAI兼容的服务
- **简单配置**: 只需配置一个API端点和密钥

### 📝 提示词系统
- **专业领域**: 医学、编程、语言学习等专业提示词
- **多语言支持**: 中文、英文等多种语言
- **难度调节**: 支持简单、中等、困难等难度级别
- **自定义提示词**: 支持创建和导入自定义提示词

## 安装说明

### 环境要求
- Python 3.8+
- 支持的操作系统: Windows, macOS, Linux

### 安装步骤

1. **克隆项目**
```bash
git clone https://github.com/your-username/anki-card-writing-assistant.git
cd anki-card-writing-assistant
```

2. **安装依赖**
```bash
pip install -r requirements.txt
```

3. **配置API密钥**
```bash
cp config/api_keys.json.example config/api_keys.json
# 编辑 config/api_keys.json 文件，填入您的API密钥
```

4. **运行程序**
```bash
python main.py --web  # 启动Web界面
# 或
python main.py --help  # 查看命令行帮助
```

## 使用指南

### 命令行使用

#### 基本用法
```bash
# 生成单张卡片
python main.py -c "Python是一种编程语言" -t Quizify -p standard_qa

# 从文件生成卡片
python main.py -f content.txt -t "Enhanced Cloze" -p cloze

# 批量生成并导出
python main.py -f content.txt -e json csv html apkg

# 生成APKG文件并导入Anki
python main.py -c "Python编程基础" -e apkg
# 生成的apkg文件可以直接导入到Anki中
```

#### 高级选项
```bash

# 设置语言和难度
python main.py -c "内容" --language zh-CN --difficulty hard

# 生成多张卡片
python main.py -c "内容" --count 5
```

#### 查看可用选项
```bash
# 列出可用模板
python main.py --list-templates

# 列出可用提示词
python main.py --list-prompts

# 列出可用LLM客户端
python main.py --list-llms
```

### Web界面使用

启动Web界面后，在浏览器中访问 `http://127.0.0.1:5000` 即可使用现代化的Web界面。

详细使用说明请参考 [WEB_README.md](WEB_README.md)

启动Web界面：
```bash
python main.py --web
```

Web界面功能：
- 现代化响应式设计
- 实时状态更新
- 文件上传支持
- 卡片预览和导航
- 多格式导出

### 配置文件

## 模板说明

### Quizify模板
- **特点**: 支持多种交互功能，包括问答、选择、填空等
- **适用场景**: 一般知识学习、语言学习等
- **字段**: Front, Back, Deck, Tags

### 增强填空模板
- **特点**: 支持提示、动画等高级填空功能
- **适用场景**: 重点内容记忆、概念理解等
- **字段**: Content, Deck, Tags

## 提示词类型

### 标准问答 (`standard_qa`)
- 生成标准的前后问答卡片
- 适合一般知识学习

### 填空卡片 (`cloze`)
- 生成填空类型的记忆卡片
- 适合重点内容记忆

### 专业领域
- **医学知识** (`medical`): 医学术语、概念、症状等
- **编程知识** (`programming`): 编程概念、语法、算法等
- **语言学习** (`language_learning`): 词汇、语法、发音等

## 导出格式

### JSON格式
- 适合程序化处理
- 包含完整的卡片数据结构

### CSV格式
- 适合Excel等工具处理
- 支持Anki直接导入

### HTML格式
- 适合网页预览
- 包含样式和交互功能

### TXT格式
- 纯文本格式
- 适合简单查看和编辑

### APKG格式
- Anki包格式，可直接导入Anki
- 使用genanki模块生成
- 支持自定义HTML/CSS模板
- 包含完整的牌组和模型信息

## 开发指南

### 项目结构
```
anki-card-writing-assistant/
├── src/                          # 源代码
│   ├── core/                     # 核心功能
│   ├── templates/                # 模板管理
│   ├── prompts/                  # 提示词管理
│   ├── utils/                    # 工具函数
│   └── web/                      # Web界面
├── config/                       # 配置文件
├── output/                       # 输出目录
├── tests/                        # 测试文件
├── main.py                       # 主程序
└── requirements.txt              # 依赖包
```

### 添加新模板
1. 在 `src/templates/` 目录下创建模板文件
2. 在 `TemplateManager` 中注册新模板
3. 更新模板配置

### 添加新提示词
1. 在 `src/prompts/` 目录下创建提示词文件
2. 在 `BasePromptManager` 中注册新提示词
3. 更新提示词配置

### 配置新的LLM服务
1. 确保目标服务支持OpenAI兼容接口
2. 在 `config/api_keys.json` 中配置API密钥和端点
3. 设置正确的模型名称

## 测试

运行测试：
```bash
pytest tests/
```

运行特定测试：
```bash
pytest tests/test_card_generator.py
```

生成测试覆盖率报告：
```bash
pytest --cov=src tests/
```

## 贡献指南

1. Fork 项目
2. 创建功能分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 打开 Pull Request

## 许可证

本项目采用 MIT 许可证 - 查看 [LICENSE](LICENSE) 文件了解详情。

## 联系方式

- 项目主页: https://github.com/your-username/anki-card-writing-assistant
- 问题反馈: https://github.com/your-username/anki-card-writing-assistant/issues
- 邮箱: contact@example.com

## 更新日志

### v1.1.0 (2024-08-28)
- 新增genanki模块支持
- 支持直接生成Anki可导入的.apkg文件
- 支持自定义HTML/CSS模板导出
- 集成Web界面APKG导出功能
- 添加APKG文件验证工具
- **Web界面APKG导出功能完善**
  - 在导出格式选择中添加APKG选项
  - 新增文件下载路由，支持所有格式的安全下载
  - 改进用户体验，APKG格式默认选中
  - 支持自定义模板APKG导出
  - 添加格式说明和使用指南

### v1.0.0 (2024-01-01)
- 初始版本发布
- 支持基本的卡片生成功能
- 支持Quizify和增强填空模板
- 支持OpenAI和Claude API
- 提供命令行和Web界面

## 致谢

- [Anki](https://apps.ankiweb.net/) - 优秀的间隔重复学习软件
- [Quizify](https://github.com/e-chehil/anki-quizify) - 优秀的Anki模板
- [OpenAI](https://openai.com/) - 提供强大的语言模型API
- [Anthropic](https://www.anthropic.com/) - 提供Claude模型API


## 设置配置

所有LLM相关设置现在都可以在Web界面中配置：

1. 启动Web应用后，点击右上角的设置按钮（⚙️）
2. 在设置模态框中配置：
   - **LLM设置**：API密钥、基础URL、模型名称、温度、最大令牌数、超时时间
   - **生成设置**：默认模板、提示词类型、语言、难度、卡片数量
   - **界面设置**：主题、语言、自动保存、预览显示

设置会实时保存到内存中，无需手动编辑配置文件。
