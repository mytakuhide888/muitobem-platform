# /srv/muitobem/app/Dockerfile
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# ---- OS依存のビルドに必要なパッケージ ----
# mysqlclient, Pillow, cryptography 等のビルド/実行に備える
RUN apt-get update && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
      build-essential \
      gcc \
      pkg-config \
      # mysqlclient 向け (Debian系は libmariadb-dev* でOK)
      libmariadb-dev-compat libmariadb-dev \
      # Pillow 向け（画像系を使わないなら外してもOK）
      libjpeg62-turbo-dev zlib1g-dev \
      # 一部ライブラリで必要になることがある
      libssl-dev libffi-dev \
      git ca-certificates \
      chromium chromium-driver fonts-liberation libnss3 libgbm1 xdg-utils \
    && rm -rf /var/lib/apt/lists/*

# 依存を先に入れてキャッシュ利用を最大化
COPY requirements.txt /app/requirements.txt
RUN pip install --upgrade pip setuptools wheel \
 && pip install --no-cache-dir -r /app/requirements.txt

# アプリ本体
COPY . /app
