![CodeRabbit Pull Request Reviews](https://img.shields.io/coderabbit/prs/github/shumizu418128/gbbinfo3.0?utm_source=oss&utm_medium=github&utm_campaign=shumizu418128%2Fgbbinfo3.0&labelColor=171717&color=FF570A&link=https%3A%2F%2Fcoderabbit.ai&label=CodeRabbit+Reviews)

```
プロジェクトルート (gbbinfojpn/urls.py)
│
├─ /admin/database/ ... gbbinfojpn/database/urls.py で管理
│    ├─ /database/test/
│    └─ /database/health/
│
└─ /app/ ... gbbinfojpn/app/urls.py で管理（今後追加予定）
     ├─ /app/xxx/
     └─ /app/yyy/
```

---

## Djangoでよく使うコマンド集

### サーバー起動
```
python manage.py runserver
```

### テスト実行
```
python manage.py test
```

---

## databaseアプリ

`gbbinfojpn/database`

- **models/** : データ構造（DBテーブル）定義のみを記述します。
    - `models.py` : Django ORMによるDBテーブル定義。
    - `supabase_client.py` : Supabase等の外部サービスと連携するためのクライアントクラス・サービスを記述します。Djangoモデルとは独立して、API経由でデータ取得・更新を行う用途で利用します。
- **views/**  : データ取得・ビジネスロジック・リクエスト処理を記述します。Django ORMやsupabase_clientを利用してデータを取得し、テンプレートやAPIレスポンスとして返却します。
- **templates/**: HTML等の出力テンプレートを配置します。

```
gbbinfojpn/
  └─ database/
      ├─ models/
      │    ├─ models.py
      │    └─ supabase_client.py   # Supabase等外部サービス用クライアント
      ├─ views/
      │    └─ views.py
      ├─ templates/
      │    └─ database/
      │         └─ *.html
      ├─ urls.py
      └─ ...
```

# Djangoにおける翻訳ファイルの準備方法

Djangoプロジェクトで多言語対応を行うための翻訳ファイル（.po, .mo）の準備手順を以下にまとめます。

## 1. 設定ファイルの確認

`settings.py` の `LANGUAGES` と `LOCALE_PATHS` を確認・設定してください。

```python
LANGUAGES = [
    ('ja', 'Japanese'),
    ('en', 'English'),
    # 必要な言語を追加
]

LOCALE_PATHS = [
    BASE_DIR / 'locale',
]
```

## 2. メッセージ抽出

プロジェクトルート（`manage.py`がある場所）で、以下のコマンドを実行して翻訳対象のメッセージを抽出します。

```sh
python manage.py makemessages -l ja  # 日本語用
python manage.py makemessages -l en  # 英語用
python manage.py makemessages -a  # 全言語一括処理
# locale/ 配下のすべての言語ディレクトリが対象
```

- `-l` オプションで言語コードを指定します。
- 必要な言語ごとにコマンドを実行してください。

## 3. 翻訳ファイル（.po）の編集

`locale/<言語コード>/LC_MESSAGES/django.po` ファイルが生成されるので、msgstr部分に翻訳を記入します。

例：
```po
msgid "Hello"
msgstr "こんにちは"
```

## 4. 翻訳ファイルのコンパイル

編集が終わったら、以下のコマンドで .po ファイルを .mo ファイルにコンパイルします。

```sh
python manage.py compilemessages
```

## 5. アプリケーションでの利用

DjangoのテンプレートやPythonコード内で、`{% trans %}` タグや `gettext` 関数を使って翻訳を呼び出します。

例：
- テンプレート: `{% trans "Hello" %}`
- Python: `from django.utils.translation import gettext as _; _('Hello')`
