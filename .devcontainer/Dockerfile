FROM python:3.11.0

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    NVM_DIR=/root/.nvm \
    NODE_VERSION=22 \
    LD_PRELOAD=/lib/x86_64-linux-gnu/libz.so.1

# Debian bullseye 已 EOL，换 archive 源；装 paddle/opencv 需要的系统库
RUN sed -i 's|deb.debian.org|archive.debian.org|g; s|security.debian.org|archive.debian.org|g' /etc/apt/sources.list \
 && apt-get -o Acquire::Check-Valid-Until=false update \
 && apt-get install -y --no-install-recommends \
      libgl1 \
      libglib2.0-0 \
      libsm6 \
      libxext6 \
      libxrender1 \
      libgomp1 \
      curl \
      git \
      ca-certificates \
 && rm -rf /var/lib/apt/lists/*

# 升级 pip 以识别 manylinux_2_28 wheel（pillow 11 用）
RUN pip install --upgrade "pip>=24.0"

# 预装后端依赖（利用层缓存；requirements.txt 变才重装）
COPY backend/requirements.txt /tmp/requirements.txt
RUN pip install -r /tmp/requirements.txt

# nvm + Node 22
RUN curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.40.1/install.sh | bash \
 && . "$NVM_DIR/nvm.sh" \
 && nvm install "$NODE_VERSION" \
 && nvm alias default "$NODE_VERSION" \
 && nvm use default \
 && NODE_BIN="$NVM_DIR/versions/node/$(nvm version default)/bin" \
 && ln -sf "$NODE_BIN/node" /usr/local/bin/node \
 && ln -sf "$NODE_BIN/npm"  /usr/local/bin/npm \
 && ln -sf "$NODE_BIN/npx"  /usr/local/bin/npx \
 && echo 'export NVM_DIR="$HOME/.nvm"' >> /root/.bashrc \
 && echo '[ -s "$NVM_DIR/nvm.sh" ] && . "$NVM_DIR/nvm.sh"' >> /root/.bashrc \
 && node -v && npm -v

WORKDIR /workspace