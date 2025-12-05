import json
import os
from typing import Dict, List, Optional, Tuple

import pandas as pd

from app.config.config import ALL_DATA
from app.util.filter_eq import Operator


class SupabaseFallback:
    def __init__(self):
        pass

    # MARK: internal helpers
    def _load_backup_csv(self, table: str, backup_root: str) -> Optional[pd.DataFrame]:
        """バックアップCSVを読み込む。存在しなければNoneを返す。"""
        csv_path = os.path.join(backup_root, f"{table}_rows.csv")
        if not os.path.exists(csv_path):
            return None
        return pd.read_csv(csv_path)

    def _split_join_columns(
        self, join_columns
    ) -> Tuple[Optional[List[str]], Dict[str, List[str]]]:
        """JOIN指定から通常カラムとネストJOINの定義を分離する。"""
        if join_columns is None or join_columns == ALL_DATA:
            return None, {}

        if not isinstance(join_columns, list):
            join_columns = [join_columns]

        columns: List[str] = []
        nested: Dict[str, List[str]] = {}
        for col in join_columns:
            if isinstance(col, str) and "(" in col and col.endswith(")"):
                table_name, inner = col.split("(", 1)
                nested_columns = [c.strip() for c in inner[:-1].split(",") if c.strip()]
                nested[table_name.strip()] = nested_columns
            else:
                columns.append(col)

        return (columns if columns else None), nested

    def _detect_join_keys(
        self,
        parent_df: pd.DataFrame,
        child_df: pd.DataFrame,
        parent_table: str,
        child_table: str,
    ) -> Tuple[Optional[str], Optional[str], str]:
        """親子の結合キーを推定する。戻り値は(親キー, 子キー, 関連タイプ)。"""
        parent_table_lower = parent_table.lower()
        child_table_lower = child_table.lower()

        # 1:N（子に parent_id がある）
        child_fk = f"{parent_table_lower}_id"
        if child_fk in child_df.columns and "id" in parent_df.columns:
            return "id", child_fk, "one-to-many"

        # N:1（親に child_id がある）
        parent_fk = f"{child_table_lower}_id"
        if parent_fk in parent_df.columns and "id" in child_df.columns:
            return parent_fk, "id", "many-to-one"

        # 同名カラムがある場合はそれで結合（iso_code など）
        commons = [c for c in parent_df.columns if c in child_df.columns]
        if commons:
            key = commons[0]
            # 子側が一意かどうかで関係性を推定
            relation = "many-to-one"
            if child_df.duplicated(subset=[key]).any():
                relation = "one-to-many"
            return key, key, relation

        return None, None, "unknown"

    def _apply_joins(
        self,
        df: pd.DataFrame,
        table: str,
        join_tables: Optional[dict],
        backup_root: str,
    ) -> pd.DataFrame:
        """DataFrameにJOIN結果を埋め込む。"""
        if not join_tables:
            return df

        for join_table, join_columns in join_tables.items():
            child_df = self._load_backup_csv(join_table, backup_root)
            if child_df is None:
                # バックアップがない場合は空を埋めてスキップ
                df[join_table] = [] if len(df) > 0 else []
                continue

            # ネストJOINの準備
            columns, nested = self._split_join_columns(join_columns)

            # ネストJOINを先に適用
            if nested:
                child_df = self._apply_joins(
                    child_df.copy(), join_table, nested, backup_root
                )

            parent_key, child_key, relation = self._detect_join_keys(
                df, child_df, table, join_table
            )
            if not parent_key or not child_key:
                df[join_table] = [] if relation == "one-to-many" else None
                continue

            # 子のカラム選択（結合キーは残す）
            if columns is None:
                child_selected = child_df.copy()
            else:
                needed_cols = set(columns)
                needed_cols.add(child_key)
                if nested:
                    needed_cols.update(nested.keys())
                child_selected = child_df[
                    [c for c in child_df.columns if c in needed_cols]
                ]

            # 最終的に返す際に結合キーを含めない場合の判定
            drop_child_key = columns is not None and child_key not in columns

            if relation == "one-to-many":
                grouped = child_selected.groupby(child_key)

                def collect_rows(val):
                    if pd.isna(val) or val not in grouped.groups:
                        return []
                    rows = grouped.get_group(val)
                    if drop_child_key and child_key in rows.columns:
                        rows = rows.drop(columns=[child_key])
                    return rows.to_dict(orient="records")

                df[join_table] = df[parent_key].apply(collect_rows)
            else:
                # many-to-one または unknown の場合は最初にマッチしたものを採用
                child_map = child_selected.set_index(child_key).to_dict(orient="index")

                def pick_row(val):
                    row = child_map.get(val)
                    if row is None:
                        return None
                    if drop_child_key:
                        row = {k: v for k, v in row.items() if k != child_key}
                    return row

                df[join_table] = df[parent_key].apply(pick_row)

        return df

    # MARK: get fallback
    def get_data_fallback(
        self,
        table,
        columns,
        order_by,
        join_tables,
        filters,
        pandas,
        timeout,
        raise_error,
        **filters_eq,
    ):
        """Supabase取得失敗時のフォールバックとしてバックアップCSVからデータを取得する。

        Args:
            table (str): 取得対象のテーブル名。`backup` ディレクトリに `<table>_rows.csv` が存在することが前提。
            columns (list[str] | None): 取得するカラム。None の場合は全カラム。
            order_by (str | None): 並び替え条件。`-` プレフィックスで降順。
            join_tables (dict | None): JOIN 指定。`{"Country": ["names"]}` のように指定し、ネストJOINも `"Member(names,Country(iso_code))"` 形式で一部対応。
            filters (dict | None): 高度なフィルター。`<field>__<operator>` 形式をサポート（部分的）。
            pandas (bool): True の場合は pandas.DataFrame を返す。
            timeout (int): キャッシュ有効期限（未使用だがインターフェースを揃えるため保持）。
            raise_error (bool): True の場合、致命的エラー時に例外を再送出。
            **filters_eq: 等価フィルター。

        Returns:
            list[dict] | pandas.DataFrame: 取得したデータ。
        """
        # ここに書かないと循環インポートになる
        from app.main import flask_cache

        cache_key = self._generate_cache_key(
            table=table,
            columns=columns,
            order_by=order_by,
            join_tables=join_tables,
            filters=filters,
            **filters_eq,
        )

        cached_data = flask_cache.get(cache_key)
        if cached_data is not None:
            if pandas:
                return pd.DataFrame(cached_data, index=None)
            return cached_data

        backup_root = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "..", "..", "backup")
        )
        csv_path = os.path.join(backup_root, f"{table}_rows.csv")

        if not os.path.exists(csv_path):
            message = f"フォールバック用CSVが見つかりません: {csv_path}"
            print(message, flush=True)
            if raise_error:
                raise FileNotFoundError(message)
            return pd.DataFrame() if pandas else []

        try:
            df = pd.read_csv(csv_path)
        except Exception as e:
            print(f"CSV読み込みに失敗しました: {e}", flush=True)
            if raise_error:
                raise e
            return pd.DataFrame() if pandas else []

        def _apply_pandas_filter(frame: pd.DataFrame, field: str, operator: str, value):
            if field not in frame.columns:
                return frame
            series = frame[field]
            if operator == Operator.GREATER_THAN:
                mask = series > value
            elif operator == Operator.GREATER_THAN_OR_EQUAL_TO:
                mask = series >= value
            elif operator == Operator.LESS_THAN:
                mask = series < value
            elif operator == Operator.LESS_THAN_OR_EQUAL_TO:
                mask = series <= value
            elif operator == Operator.NOT_EQUAL:
                mask = series != value
            elif operator == Operator.LIKE:
                mask = series.astype(str).str.contains(str(value), case=True, na=False)
            elif operator == Operator.ILIKE:
                mask = series.astype(str).str.contains(str(value), case=False, na=False)
            elif operator == Operator.NOT_LIKE:
                mask = ~series.astype(str).str.contains(str(value), case=True, na=False)
            elif operator == Operator.NOT_ILIKE:
                mask = ~series.astype(str).str.contains(
                    str(value), case=False, na=False
                )
            elif operator == Operator.IS:
                mask = series.isna()
            elif operator == Operator.IS_NOT:
                mask = series.notna()
            elif operator == Operator.IN_:
                mask = series.isin(
                    value if isinstance(value, (list, tuple, set)) else [value]
                )
            elif operator == Operator.CONTAINS:
                mask = series.apply(
                    lambda v: value in v if isinstance(v, (list, dict, set)) else False
                )
            else:
                mask = series == value
            return frame[mask]

        # 高度なフィルタ
        if filters:
            for filter_key, value in filters.items():
                if "__" in filter_key:
                    field, operator = filter_key.split("__", 1)
                    df = _apply_pandas_filter(df, field, operator, value)
                else:
                    if filter_key in df.columns:
                        df = df[df[filter_key] == value]

        # 等価フィルタ
        for key, value in filters_eq.items():
            if key in df.columns:
                df = df[df[key] == value]

        # JOIN の適用（親のフィルタ後に実施）
        df = self._apply_joins(df, table, join_tables, backup_root)

        # カラム選択
        if columns:
            selected = [col for col in columns if col in df.columns]
            # JOIN結果は drop しない
            selected.extend([jt for jt in (join_tables or {}) if jt in df.columns])
            df = df[selected]

        # 並び替え
        if order_by:
            descending = order_by.startswith("-")
            sort_key = order_by[1:] if descending else order_by
            if sort_key in df.columns:
                df = df.sort_values(by=sort_key, ascending=not descending)

        records = df.to_dict(orient="records")
        flask_cache.set(cache_key, records, timeout=timeout)

        if pandas:
            return pd.DataFrame(records, index=None)
        return records

    # MARK: tavily fallback
    def get_tavily_data_fallback(self, cache_key: str, column: str, raise_error: bool):
        """Tavilyデータのフォールバック取得を行う。

        Supabase取得が失敗した場合に、`backup/Tavily_rows.csv` から
        指定カラムのデータを取得する。

        Args:
            cache_key (str): 取得対象データを識別するキー。
            column (str): 取得するカラム名。
            raise_error (bool): True の場合、致命的エラー時に例外を再送出。

        Returns:
            Any: 指定カラムの値。該当データがない場合は空リスト。
        """
        # ここに書かないと循環インポートになる
        from app.main import flask_cache

        cached = flask_cache.get(cache_key + "_" + column)
        if cached is not None:
            return cached

        backup_root = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "..", "..", "backup")
        )
        csv_path = os.path.join(backup_root, "Tavily_rows.csv")

        if not os.path.exists(csv_path):
            message = f"フォールバック用CSVが見つかりません: {csv_path}"
            print(message, flush=True)
            if raise_error:
                raise FileNotFoundError(message)
            return []

        try:
            df = pd.read_csv(csv_path)
        except Exception as e:
            print(f"Tavily CSV読み込みに失敗しました: {e}", flush=True)
            if raise_error:
                raise e
            return []

        if "cache_key" not in df.columns or column not in df.columns:
            message = f"Tavily CSVに必要なカラムがありません: cache_key / {column}"
            print(message, flush=True)
            if raise_error:
                raise KeyError(message)
            return []

        target = df[df["cache_key"] == cache_key]
        if target.empty:
            return []

        # 先頭行のみ使用（DB同等の想定）
        value = target.iloc[0][column]

        if pd.isna(value):
            data = []
        elif isinstance(value, str):
            try:
                data = json.loads(value)
            except Exception:
                # 文字列のまま保持せず、安全側で空配列にする
                data = []
        else:
            data = value

        # キャッシュ保存
        flask_cache.set(cache_key + "_" + column, data)
        return data


supabase_fallback = SupabaseFallback()
