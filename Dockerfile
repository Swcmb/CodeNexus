# ============================================================
# CodeNexus Dockerfile
# 多阶段构建：构建阶段 + 运行阶段
# ============================================================

# ---- 构建阶段 ----
FROM python:3.9-slim AS builder

WORKDIR /build

# 使用国内 Debian 镜像源
RUN sed -i 's|http://deb.debian.org|https://mirrors.aliyun.com|g' /etc/apt/sources.list.d/debian.sources 2>/dev/null || \
    sed -i 's|http://deb.debian.org|https://mirrors.aliyun.com|g' /etc/apt/sources.list 2>/dev/null || true

# 安装系统依赖（tree-sitter 编译需要 C 编译器）
RUN apt-get update && \
    apt-get install -y --no-install-recommends gcc g++ && \
    rm -rf /var/lib/apt/lists/*

# 复制依赖文件并安装（使用国内 pip 镜像源）
COPY pyproject.toml requirements.txt ./
RUN pip install --no-cache-dir --prefix=/install \
    -i https://mirrors.aliyun.com/pypi/simple/ --trusted-host mirrors.aliyun.com \
    -r requirements.txt

# ---- 运行阶段 ----
FROM python:3.9-slim AS runtime

LABEL maintainer="codenexus Team <team@codenexus.dev>"
LABEL description="CodeNexus - 智能代码分析与知识图谱构建工具"
LABEL version="0.1.0"

# 使用国内 Debian 镜像源
RUN sed -i 's|http://deb.debian.org|https://mirrors.aliyun.com|g' /etc/apt/sources.list.d/debian.sources 2>/dev/null || \
    sed -i 's|http://deb.debian.org|https://mirrors.aliyun.com|g' /etc/apt/sources.list 2>/dev/null || true

# 安装运行时依赖并创建非 root 用户
RUN apt-get update && \
    apt-get install -y --no-install-recommends curl && \
    rm -rf /var/lib/apt/lists/* && \
    groupadd -r codenexus && \
    useradd -r -g codenexus -d /app -s /sbin/nologin codenexus

WORKDIR /app

# 从构建阶段复制已安装的 Python 包
COPY --from=builder /install /usr/local

# 复制项目源码
COPY src/ ./src/
COPY pyproject.toml requirements.txt ./

# 安装项目本身
RUN pip install --no-cache-dir \
    -i https://mirrors.aliyun.com/pypi/simple/ --trusted-host mirrors.aliyun.com \
    .

# 复制配置模板
COPY .env.example ./

# 创建日志目录并设置权限
RUN mkdir -p /app/logs && chown -R codenexus:codenexus /app

# 切换到非 root 用户
USER codenexus

# 环境变量
ENV SERVER_HOST=0.0.0.0 \
    SERVER_PORT=8000 \
    SERVER_WORKERS=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# 暴露端口
EXPOSE 8000

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --retries=3 --start-period=15s \
    CMD python -c "import httpx; httpx.get('http://localhost:8000/api/v1/health').raise_for_status()" || exit 1

# 启动命令
CMD ["python", "-m", "uvicorn", "codenexus.api.app:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
