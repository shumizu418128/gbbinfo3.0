# Python 3.12をベースイメージとして使用
FROM python:3.12-slim

# システムパッケージの更新と必要なライブラリのインストール
RUN apt-get update && apt-get install -y \
    postgresql-client \
    libpq-dev \
    gcc \
    curl \
    gettext \
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

# ディレクトリの所有者を変更
RUN chown -R appuser:appuser /app

# 非rootユーザーに切り替え
USER appuser

# 静的ファイルを収集
RUN python manage.py collectstatic --noinput

# 翻訳ファイルをコンパイル
RUN python manage.py compilemessages

# ポート8000を公開
EXPOSE 8000

# GunicornでDjangoアプリケーションを起動
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "--workers", "3", "--timeout", "120", "gbbinfojpn.wsgi:application"]
