"""
pytest 共通設定。

テストセッション開始時にバックグラウンドタスク（get_translated_urls）の
スレッド起動を無効化する。これにより、どのテストファイルが先に app.main を
インポートしても、別スレッドが with を抜けた後の本物の Supabase を参照して
KeyError になることを防ぐ。
"""
# Flask 3 で削除された locked_cached_property の互換（flask-babel が参照する）。
# Flask 3 では flask.helpers.cached_property も削除されているため werkzeug から取得する。
import flask.helpers

if not hasattr(flask.helpers, "locked_cached_property"):
    from werkzeug.utils import cached_property

    flask.helpers.locked_cached_property = cached_property

import app.context_processors  # noqa: F401 - patch が app.context_processors を参照する前にモジュールを読み込む

from unittest.mock import patch

_patch_bg_tasks = patch(
    "app.context_processors.initialize_background_tasks", lambda x: None
)
_patch_bg_tasks.start()
