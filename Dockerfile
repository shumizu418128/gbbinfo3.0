# Python 3.12をベースイメージとして使用
FROM python:3.12-slim

ENV TZ=Asia/Tokyo

RUN apt-get update && apt-get install -y \
    postgresql-client \
    libpq-dev \
    gcc \
    curl \
    gettext \
    tzdata \
    && rm -rf /var/lib/apt/lists/*

# uvをインストール
RUN pip install --no-cache-dir uv

# 非rootユーザーを作成（セキュリティ向上）
RUN useradd --create-home --shell /bin/bash appuser

# 作業ディレクトリを設定
WORKDIR /app

# 依存関係ファイルをコピー
COPY requirements.txt .

# Python依存関係をインストール
RUN uv pip install --no-cache --system -r requirements.txt

# アプリケーションコードをコピー
COPY . .

EXPOSE 8080

# その後にFlaskアプリケーションを起動
CMD ["waitress-serve", "--host=0.0.0.0", "--port=8080", "--call", "app.main:main"]
