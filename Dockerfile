# syntax=docker/dockerfile:1

FROM python:3.11-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl ca-certificates \
 && rm -rf /var/lib/apt/lists/*

# 复制依赖清单并安装
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# 复制项目代码
COPY . .

# 确保入口脚本可执行
RUN chmod +x /app/docker-entrypoint.sh

EXPOSE 5000

# 缺省环境变量（可被 .env 或 -e 覆盖）
ENV HOST=0.0.0.0 \
    PORT=5000 \
    FLASK_DEBUG=false \
    EXPORT_OUTPUT_DIR=output \
    TEMPLATES_DIR="Card Template"

ENTRYPOINT ["/app/docker-entrypoint.sh"]
