class Operator:
    # 比較演算子
    GREATER_THAN = "gt"  # より大きい
    GREATER_THAN_OR_EQUAL_TO = "gte"  # 以上
    LESS_THAN = "lt"  # より小さい
    LESS_THAN_OR_EQUAL_TO = "lte"  # 以下
    EQUAL = "eq"  # 等しい
    NOT_EQUAL = "neq"  # 等しくない

    # 部分一致
    LIKE = "like"  # 部分一致
    ILIKE = "ilike"  # 大文字小文字を区別しない部分一致
    NOT_LIKE = "not_like"  # 部分一致の否定
    NOT_ILIKE = "not_ilike"  # 大文字小文字を区別しない部分一致の否定

    # NULL判定
    IS = "is"  # Noneと等しい
    IS_NOT = "is_not"  # Noneと等しくない

    # リスト・配列
    IN_ = "in"  # リストに含まれる
    CONTAINS = "contains"  # 配列が値を含む

    # 用途別エイリアス（汎用的に使える日本語的な名前）
    MATCH = LIKE  # 部分一致
    MATCH_IGNORE_CASE = ILIKE  # 大文字小文字を区別しない部分一致
    IN_LIST = IN_  # リストに含まれる
    ARRAY_CONTAINS = CONTAINS  # 配列が値を含む
