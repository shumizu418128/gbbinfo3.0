#!/usr/bin/env python3
"""
国名を更新するスクリプト
SupabaseのCountryテーブルに新しい言語の国名を追加する
"""

import sys
from pathlib import Path

# プロジェクトのルートディレクトリをパスに追加
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


from app.models.supabase_client import SupabaseService  # noqa: E402


def main():
    try:
        # SupabaseServiceのインスタンスを作成
        supabase_service = SupabaseService()

        # 国名を更新
        # 追加する言語コードのリスト
        add_langs = ["ar", "be", "da", "ga"]

        # 削除する言語コードのリスト
        remove_langs = []

        print(f"以下の言語の国名を追加します: {', '.join(add_langs)}")
        print("処理を開始します...")

        supabase_service.update_country_names(
            add_langs=add_langs, remove_langs=remove_langs
        )

        print("国名の更新が完了しました。")

    except Exception as e:
        print(f"エラーが発生しました: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
