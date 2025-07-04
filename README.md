![CodeRabbit Pull Request Reviews](https://img.shields.io/coderabbit/prs/github/shumizu418128/gbbinfo3.0?utm_source=oss&utm_medium=github&utm_campaign=shumizu418128%2Fgbbinfo3.0&labelColor=171717&color=FF570A&link=https%3A%2F%2Fcoderabbit.ai&label=CodeRabbit+Reviews)

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
