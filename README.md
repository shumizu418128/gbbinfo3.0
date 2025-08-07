# GBB Info 3.0

Grand Beatbox Battle (GBB) の情報を集約・提供するウェブアプリケーションです。

## 主な機能

- 過去の大会結果の閲覧
- 出場者の情報検索
- AIによる出場者情報の検索（Google Gemini, Tavily API連携）
- 多言語対応

## 使用技術

- **バックエンド**: Flask (Python)
- **フロントエンド**: HTML, CSS, JavaScript
- **データベース**: Supabase
- **AI**: Google Gemini, Tavily API
- **デプロイ**: Docker

---

## 実行方法

### 1. ローカルでの開発サーバー起動

リポジトリをクローンし、必要なライブラリをインストールします。

```sh
pip install -r requirements.txt
```

環境変数（`.env`ファイルなど）を設定した後、以下のコマンドで開発サーバーを起動します。

```sh
python run.py
```

サーバーは `http://localhost:10000` で起動します。

### 2. Dockerでの実行

以下のコマンドでDockerイメージをビルドし、コンテナを実行します。

```sh
# Dockerイメージのビルド
docker build -t gbbinfo .

# Dockerコンテナの実行
docker run -p 10000:10000 --env-file .env gbbinfo
```

---

## ディレクトリ構成の概要

```
gbbinfo3.0/
├── run.py                    # アプリケーション起動スクリプト
├── app/
│   ├── main.py               # Flaskアプリケーションのインスタンス、ルーティング定義
│   ├── settings.py           # アプリケーション設定
│   ├── models/               # データベースや外部APIのクライアント
│   │   ├── supabase_client.py
│   │   └── gemini_client.py
│   ├── views/                # 各エンドポイントの処理ロジック
│   ├── templates/            # HTMLテンプレート
│   ├── static/               # CSS, JavaScript, 画像ファイル
│   └── translations/         # 翻訳ファイル (Flask-Babel)
├── requirements.txt          # Pythonライブラリの依存関係
└── Dockerfile                # Dockerコンテナ定義
```

---

## 翻訳ファイルの更新手順 (Flask-Babel)

本プロジェクトでは `Flask-Babel` を利用して多言語対応を行っています。

### 1. 翻訳対象のテキストを抽出

以下のコマンドを実行し、ソースコードから翻訳対象の文字列を抽出し、`messages.pot`ファイルを更新します。

```sh
pybabel extract -F app/babel.cfg -o app/messages.pot app/
```

### 2. 各言語の翻訳ファイルを更新

`.pot`ファイルの更新内容を、各言語の`.po`ファイルに反映させます。

```sh
pybabel update -i app/messages.pot -d app/translations
```

### 3. 翻訳ファイルを編集

`app/translations/<言語コード>/LC_MESSAGES/messages.po` ファイルを開き、`msgstr` に翻訳後のテキストを追記・修正します。

### 4. 翻訳ファイルをコンパイル

編集した`.po`ファイルを、アプリケーションが利用する`.mo`ファイルにコンパイルします。

```sh
pybabel compile -d app/translations
```