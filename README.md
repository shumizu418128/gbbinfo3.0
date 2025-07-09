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
