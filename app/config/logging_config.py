import logging
import os
import sys
from pathlib import Path


def setup_logging():
    """
    アプリケーション全体のロギング設定を行う。

    各ログメッセージには関数名とファイル名が含まれ、
    ローカル環境ではファイルとコンソール、本番環境ではコンソールのみに出力される。
    """
    # 環境変数で本番環境かどうかを判定
    is_production = os.getenv("ENVIRONMENT_CHECK") != "qawsedrftgyhujikolp"

    # ログフォーマットを設定（関数名とファイル名を含む）
    formatter = logging.Formatter(
        "%(levelname)s - %(name)s.%(filename)s:%(funcName)s:%(lineno)d - %(message)s"
    )

    # ルートロガーの設定
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)

    # ハンドラーを追加（重複を避けるため、既存のハンドラーをクリア）
    if root_logger.handlers:
        root_logger.handlers.clear()

    # コンソールハンドラー（常に追加）
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    # ファイルハンドラー（ローカル環境のみ）
    if not is_production:
        # ログディレクトリを作成
        log_dir = Path(__file__).parent.parent.parent / "logs"
        log_dir.mkdir(exist_ok=True)

        # ログファイルのパス
        log_file = log_dir / "app.log"

        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)

    # 外部ライブラリのログレベルを調整
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("requests").setLevel(logging.WARNING)

    # werkzeug と httpx のログを無効化]
    if is_production:
        werkzeug_logger = logging.getLogger("werkzeug")
        werkzeug_logger.propagate = False
        werkzeug_logger.disabled = True

        httpx_logger = logging.getLogger("httpx")
        httpx_logger.propagate = False
        httpx_logger.disabled = True

    # waitress.queue ロガーを無効化
    waitress_queue_logger = logging.getLogger("waitress.queue")
    waitress_queue_logger.propagate = False
    waitress_queue_logger.disabled = True


def get_logger(name: str) -> logging.Logger:
    """
    指定された名前のロガーを取得する。

    Args:
        name (str): ロガー名（通常は__name__を使用）

    Returns:
        logging.Logger: 設定済みのロガー
    """
    return logging.getLogger(name)
