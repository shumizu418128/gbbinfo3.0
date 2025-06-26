from django.core.exceptions import ValidationError


def validate_language_keys(value, allowed_languages):
    """
    多言語JSONフィールドの言語キーを検証するバリデーター

    Args:
        value: 検証するJSON値
        allowed_languages: 許可される言語のリスト (settings.LANGUAGESから取得)

    Raises:
        ValidationError: 無効な言語キーが含まれている場合
    """
    if not isinstance(value, dict):
        raise ValidationError("値は辞書形式である必要があります")

    # 許可される言語コードを抽出
    allowed_codes = [lang[0] for lang in allowed_languages]

    # 無効な言語キーをチェック
    invalid_keys = []
    for key in value.keys():
        if key not in allowed_codes:
            invalid_keys.append(key)

    if invalid_keys:
        raise ValidationError(
            "無効な言語キーが含まれています: %(invalid_keys)s. "
            "許可される言語: %(allowed_languages)s",
            params={
                "invalid_keys": ", ".join(invalid_keys),
                "allowed_languages": ", ".join(allowed_codes),
            },
        )

    # 空の辞書は許可しない
    if not value:
        raise ValidationError("値が空です")

    # 少なくとも1つの言語が必須
    if not any(value.values()):
        raise ValidationError("少なくとも1つの言語で値が設定されている必要があります")
