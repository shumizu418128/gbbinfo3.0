"""
キャッシュ処理専用モジュール
年度・カテゴリデータのキャッシュ管理を行う
"""

from django.core.cache import cache

from gbbinfojpn.common.filter_eq import Operator
from gbbinfojpn.database.models.supabase_client import supabase_service


def get_category_by_year(filter_cancelled_year: bool = False):
    """
    年度ごとのカテゴリ情報を {year: [category_id, ...]} の形で返す

    Args:
        filter_cancelled_year (bool, optional): Trueの場合、キャンセルされた年度（categoriesがNULLのもの）を除外する。デフォルトはFalse。

    Returns:
        dict: {year: [category_id, ...]} の形式の辞書。エラー時は空辞書。

    Note:
        - キャッシュキーは "category_by_year" で固定。
        - SupabaseのYearテーブルから "year" および "categories" カラムを取得。
        - categoriesがNULLの年度は、filter_cancelled_year=Trueのとき除外される。
    """
    cache_key = "category_by_year"
    category_by_year = cache.get(cache_key)

    # キャンセル年度を除外する場合はフィルターを適用
    if filter_cancelled_year:
        filters = {f"categories__{Operator.IS_NOT}": None}
    else:
        filters = {}

    if category_by_year is None:
        # DBから取得
        year_data = supabase_service.get_data(
            table="Year",
            columns=["year", "categories"],
            filters=filters,
        )
        # {year: [category_id, ...]} の形に変換
        category_by_year = {}
        for item in year_data:
            year = item.get("year")
            categories = item.get("categories") or []
            category_by_year[year] = categories
        cache.set(cache_key, category_by_year)
    return category_by_year


def get_all_categories():
    """
    全カテゴリデータをキャッシュから取得（なければDBから取得してキャッシュし、id→nameの辞書で返す）

    Args:
        なし

    Returns:
        dict: {id: name} の形式の辞書。カテゴリが存在しない場合は空辞書。

    Note:
        - キャッシュキーは "all_categories" で固定。
        - SupabaseのCategoryテーブルから "id" および "name" カラムを取得。
        - 取得時は display_order でソートされる。
    """
    cache_key = "all_categories"
    categories_dict = cache.get(cache_key)

    if categories_dict is None:
        categories = supabase_service.get_data(
            table="Category",
            order_by="display_order",
            columns=["id", "name"],
        )
        # id→nameの辞書に変換
        categories_dict = {category["id"]: category["name"] for category in categories}
        cache.set(cache_key, categories_dict)

    return categories_dict


def get_category_name_to_id_mapping():
    """
    カテゴリのname→idマッピング辞書を返す

    Returns:
        dict: {name: id} の形式の辞書。カテゴリが存在しない場合は空辞書。

    Note:
        - get_all_categories()を利用してid→nameマッピングを取得し、逆引き辞書を作成。
    """
    id_to_name = get_all_categories()
    return {name: category_id for category_id, name in id_to_name.items()}


def get_category_id_by_name(category_name: str) -> int:
    """
    カテゴリ名からIDを取得する

    Args:
        category_name (str): カテゴリ名

    Returns:
        int: カテゴリID

    Raises:
        ValueError: 指定されたカテゴリ名が存在しない場合
    """
    name_to_id = get_category_name_to_id_mapping()
    if category_name not in name_to_id:
        raise ValueError(f"指定されたカテゴリ名が存在しません: {category_name}")

    id = name_to_id[category_name]
    if not isinstance(id, int):
        raise ValueError(f"カテゴリIDが整数ではありません: {id}")

    return id


def get_categories_for_year(year: int):
    """
    指定した年度のカテゴリ一覧を取得する

    Args:
        year (int): 取得したい年度

    Returns:
        list[dict]: 指定年度のカテゴリ情報のリスト。各要素は {category_id: category_name} の辞書。

    Raises:
        ValueError: 指定された年度のカテゴリ情報が存在しない場合

    Note:
        - 年度ごとのカテゴリIDリストと、全カテゴリのID→名前マッピングを利用してカテゴリ情報を返す。
    """

    # 年度データ {year: [category_id, ...]}
    categories_per_year = get_category_by_year(filter_cancelled_year=True)

    years = [int(y) for y in categories_per_year.keys()]

    # カテゴリデータ {id: name}
    all_categories = get_all_categories()

    # 指定年度のカテゴリ情報を取得
    categories_for_year = []

    if year in years:
        categories_list = categories_per_year[year]
        categories_for_year = [
            {category_id: all_categories[category_id]}
            for category_id in categories_list
        ]
        return categories_for_year

    raise ValueError(f"指定年度のカテゴリ情報が見つかりません: {year}")
