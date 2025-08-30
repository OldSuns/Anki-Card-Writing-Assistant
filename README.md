# Anki 写卡助手

<img src="https://github.com/user-attachments/assets/8575c2e7-7a34-46ea-ab20-d29689f52d37" alt="Anki_Assistant" width="700">

基于大语言模型的 Anki 卡片生成工具，支持 Web 界面和多格式导出。

## 特性

- **智能生成**：使用 LLM 生成高质量 Anki 卡片，支持多种模板
- **多格式导出**：JSON、CSV、APKG、TXT、HTML 五种格式一键导出
- **Web 界面**：可视化操作，实时预览和历史记录管理
- **文件支持**：处理 TXT、MD、DOCX、PDF、XLSX 等多种文件格式
- **灵活配置**：支持自定义提示词和 LLM 参数

## 快速开始

### Docker 部署（推荐）

使用预构建的 Docker 镜像快速部署，支持两种安装方式：

#### 方式一：Docker 直接安装

1. **安装 Docker**：
   - Windows/macOS：下载并安装 [Docker Desktop](https://www.docker.com/products/docker-desktop/)
   - Linux：参考 [Docker 官方安装指南](https://docs.docker.com/engine/install/)

2. **配置环境**：
```bash
# 创建项目目录
mkdir anki-assistant && cd anki-assistant

# 下载配置文件
curl -O https://raw.githubusercontent.com/OldSuns/Anki-Card-Writing-Assistant/main/env.example
curl -O https://raw.githubusercontent.com/OldSuns/Anki-Card-Writing-Assistant/main/docker-compose.yml

# 配置 API 密钥
cp env.example .env
# 编辑 .env 文件，设置 LLM_API_KEY
```

3. **启动服务**：
```bash
# 拉取并启动容器
docker run -d \
  --name anki-assistant \
  -p 5000:5000 \
  -v $(pwd)/output:/app/output \
  -v $(pwd)/logs:/app/logs \
  --env-file .env \
  ghcr.io/oldsuns/anki-card-writing-assistant:latest

# 查看容器状态
docker ps

# 查看日志
docker logs -f anki-assistant
```

4. **访问应用**：浏览器打开 `http://localhost:5000`

#### 方式二：Docker Compose 安装

1. **安装 Docker Compose**：
   - 通常随 Docker Desktop 一起安装
   - Linux 用户可单独安装：`sudo apt-get install docker-compose-plugin`

2. **克隆项目**：
```bash
git clone https://github.com/OldSuns/Anki-Card-Writing-Assistant.git
cd Anki-Card-Writing-Assistant

# 配置 API 密钥
cp env.example .env
# 编辑 .env 文件，设置 LLM_API_KEY
```

3. **启动服务**：
```bash
# 使用预构建镜像启动
docker-compose up -d

# 查看服务状态
docker-compose ps

# 查看日志
docker-compose logs -f
```

4. **访问应用**：浏览器打开 `http://localhost:5000`

#### 镜像说明

项目使用 GitHub Container Registry 托管的预构建镜像：
- **镜像地址**：`ghcr.io/oldsuns/anki-card-writing-assistant:latest`
- **自动构建**：每次代码更新后自动构建最新镜像

#### 环境变量配置

项目提供 `env.example` 模板，主要配置项：
```env
# 必需配置
LLM_API_KEY=your_openai_api_key_here

# 可选配置
LLM_BASE_URL=https://api.openai.com/v1
LLM_MODEL=gpt-3.5-turbo
LLM_TEMPERATURE=0.7
GEN_DEFAULT_CARD_COUNT=3
PORT=5000
```

#### Docker 管理命令

**Docker 直接安装**：
```bash
# 启动容器
docker start anki-assistant

# 停止容器
docker stop anki-assistant

# 重启容器
docker restart anki-assistant

# 更新到最新版本
docker pull ghcr.io/oldsuns/anki-card-writing-assistant:latest
docker stop anki-assistant
docker rm anki-assistant
# 重新运行 docker run 命令
```

**Docker Compose 安装**：
```bash
# 启动服务
docker-compose up -d

# 停止服务
docker-compose down

# 重启服务
docker-compose restart

# 更新到最新版本
docker-compose pull && docker-compose up -d
```

#### 数据持久化

容器会自动挂载以下目录：
- `./output` - 导出的卡片文件
- `./logs` - 应用日志文件

**注意**：确保挂载目录具有适当的读写权限。

### 本地安装

```bash
# 安装依赖
pip install -r requirements.txt

# 配置文件
cp config.json.example config.json
# 编辑 config.json 设置 LLM API 配置

# 启动 Web 界面
python main.py --debug --port 5000
```

## 使用方法

### Web 界面
访问 `http://localhost:5000` 使用可视化界面：
- 上传文件或输入文本内容
- 选择模板和生成参数
- 实时查看生成进度和结果
- 下载多种格式的导出文件

## 配置说明

### 支持的模板
- **[Quizify](https://github.com/e-chehil/anki-quizify)**：基础问答卡片模板
- **[Quizify Enhanced Cloze](https://github.com/edwinaze/anki-quizify-enhanced-cloze/)**：增强型填空卡片模板
- 两款模板皆已修改以达到更佳效果。

### 提示词系统
- 全局提示词位于 `src/prompts/`
- 支持模板特定的提示词变体
- 可通过 Web 界面在线编辑和重置

### 导出格式
- **JSON**：包含完整元数据的结构化数据
- **CSV**：表格格式，便于数据分析
- **APKG**：Anki 包文件，可直接导入
- **TXT**：纯文本格式预览
- **HTML**：网页格式预览

## 故障排除

### 常见问题

1. **Docker 安装问题**
   - Windows/macOS：确保 Docker Desktop 已启动
   - Linux：检查 Docker 服务状态 `sudo systemctl status docker`
   - 验证安装：`docker --version`

2. **容器启动失败**
   - 检查 Docker 是否正确安装和运行
   - 确认 `.env` 文件配置正确
   - 查看日志：`docker logs anki-assistant` 或 `docker-compose logs -f`
   - 检查端口 5000 是否被占用

3. **无法访问 Web 界面**
   - 确认容器正在运行：`docker ps`
   - 确认端口 5000 未被占用
   - 尝试访问 `http://127.0.0.1:5000`
   - 检查防火墙设置

4. **LLM API 调用失败**
   - 检查 API 密钥是否正确设置在 `.env` 文件中
   - 确认网络连接正常
   - 查看应用日志了解详细错误

5. **导出文件下载失败**
   - 检查 `output/` 目录权限
   - 确认文件生成成功
   - 验证挂载目录是否正确

6. **镜像拉取失败**
   - 检查网络连接
   - 尝试手动拉取：`docker pull ghcr.io/oldsuns/anki-card-writing-assistant:latest`
   - 确认 GitHub Container Registry 可访问

### 日志查看
- **Docker 直接安装**：`docker logs -f anki-assistant`
- **Docker Compose 安装**：`docker-compose logs -f`
- **本地安装**：`logs/app.log`

## 开发说明

### 添加新模板
1. 在 `Card Template/` 创建模板文件夹
2. 在 `src/templates/template_manager.py` 注册模板
3. 测试 APKG 导出功能

### 自定义提示词
- 修改 `src/prompts/` 下的 Markdown 文件
- 创建 `*_user.md` 文件进行用户覆盖
- 通过 Web 界面在线编辑

### 扩展导出格式
在 `src/core/unified_exporter.py` 添加新的导出方法

## 许可证

MIT 许可证 - 详见 `LICENSE` 文件
