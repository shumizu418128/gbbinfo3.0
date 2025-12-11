import json
import os
from datetime import datetime

import gspread
import ratelimit
from google.oauth2.service_account import Credentials

SCOPE = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive",
]


class SpreadsheetService:
    """
    Googleスプレッドシートに接続し、質問と回答を記録するクライアントクラス。

    Attributes:
        credentials: Google認証情報
        client: gspreadクライアント
    """

    def __init__(self):
        """
        SpreadsheetClientの初期化
        環境変数GOOGLE_SHEET_CREDENTIALSが存在しない場合は例外を発生させます。
        """
        if os.environ.get("GOOGLE_SHEET_CREDENTIALS") is None:
            raise EnvironmentError(
                "GOOGLE_SHEET_CREDENTIALS環境変数が設定されていません。"
            )
        self._credentials = None
        self._client = None

    @property
    def client(self):
        """
        Googleスプレッドシートに接続するためのクライアントを取得します。

        環境変数から認証情報を取得し、gspreadを使用してGoogleスプレッドシートに接続します。
        認証情報が未設定の場合は、デフォルトのJSONファイルから取得します。

        Returns:
            gspread.Client: Googleスプレッドシートに接続するためのクライアントオブジェクト。
        """
        if self._credentials is None:
            # 認証情報を環境変数から取得
            path = os.environ.get("GOOGLE_SHEET_CREDENTIALS")
            credentials_info = json.loads(path)
            self._credentials = Credentials.from_service_account_info(
                credentials_info, scopes=SCOPE
            )

        if self._client is None:
            self._client = gspread.authorize(self._credentials)

        return self._client

    @ratelimit.limits(calls=1, period=4, raise_on_limit=False)
    def record_question(self, year: int, question: str, answer: str):
        """
        Googleスプレッドシートに質問と回答を記録します。
        環境変数を使用してローカル環境かどうかを判定し、スプレッドシートにデータを挿入します。

        Args:
            year (int): 質問が関連する年。
            question (str): 記録する質問。
            answer (str): 記録する回答。
        Returns:
            None: (結果を記録)
        """
        year_str = str(year)
        dt_now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # スプレッドシートを開く
        sheet = self.client.open("gbbinfo-jpn").worksheet("questions")

        # 質問と年を記録
        sheet.insert_row([dt_now, year_str, question, answer], 2)

    def get_notice(self):
        """
        Googleスプレッドシートからお知らせを取得します。

        Returns:
            str: お知らせの内容
        """
        # ここに書かないと循環インポートになる
        from app.main import flask_cache

        notice_cache_key = "spreadsheet_notice"
        timestamp_cache_key = "spreadsheet_timestamp"

        cached_notice = flask_cache.get(notice_cache_key)
        cached_timestamp = flask_cache.get(timestamp_cache_key)

        if cached_notice and cached_timestamp:
            return cached_notice, cached_timestamp

        # スプレッドシートを開く
        sheet = self.client.open("gbbinfo-jpn").worksheet("notice")

        # お知らせを取得
        notice = sheet.acell("A1").value or ""
        timestamp = sheet.acell("B1").value or ""

        flask_cache.set(notice_cache_key, notice, timeout=10)
        flask_cache.set(timestamp_cache_key, timestamp, timeout=10)

        return notice, timestamp


# グローバルインスタンス
spreadsheet_service = SpreadsheetService()
