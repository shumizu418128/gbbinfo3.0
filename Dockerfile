FROM python:3.13-slim

ENV TZ=Asia/Tokyo

RUN apt-get update && apt-get install -y --no-install-recommends \
    postgresql-client \
    curl \
    gettext \
    tzdata \
    && rm -rf /var/lib/apt/lists/*

# uvをインストール
RUN pip install --no-cache-dir uv

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
