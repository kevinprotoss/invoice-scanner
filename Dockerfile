# ---------- Stage 1: frontend build ----------
FROM node:22-slim AS frontend
WORKDIR /app

COPY frontend/package.json frontend/package-lock.json* ./
RUN npm ci

COPY frontend/ ./
RUN VITE_OUT_DIR=dist npm run build

# ---------- Stage 2: runtime ----------
FROM python:3.11.0

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    APP_DATA_DIR=/data

# Debian bullseye 已 EOL：换 archive 源，跳过 Valid-Until 校验
# 安装 opencv / paddle 所需系统库
RUN sed -i 's|deb.debian.org|archive.debian.org|g; s|security.debian.org|archive.debian.org|g' /etc/apt/sources.list \
 && apt-get -o Acquire::Check-Valid-Until=false update \
 && apt-get install -y --no-install-recommends \
      libgl1 \
      libglib2.0-0 \
      libsm6 \
      libxext6 \
      libxrender1 \
      libgomp1 \
 && rm -rf /var/lib/apt/lists/*

# pip 22.2.2 不识别 manylinux_2_28（pillow 11 的 wheel 是 manylinux_2_28）
# 只升级 pip 自身，不动业务依赖
RUN pip install --no-cache-dir --upgrade "pip>=24.0"

# paddlepaddle 2.6.2 动态链接 zlib 失败，强制优先加载系统 libz
ENV LD_PRELOAD=/lib/x86_64-linux-gnu/libz.so.1

WORKDIR /app

# 后端依赖单独复制，利用层缓存
COPY backend/requirements.txt ./backend/
RUN pip install --no-cache-dir -r backend/requirements.txt

# 后端源码
COPY backend/ ./backend/

# OCR 模块（ocr_service.py 会把 /app 加入 sys.path）
COPY ocr/ ./ocr/

# 前端产物
COPY --from=frontend /app/dist ./backend/app/static

EXPOSE 8000

WORKDIR /app/backend
CMD ["python", "run.py"]